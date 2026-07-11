from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator

from core.models import Logs, SystemMembership, Systems, Address
from core.utils import get_client_ip, get_user_agent, decrypt, encrypt
from core.decorators import require_system_access, require_system_role, require_superadmin

from .models import (
    StudentProfile, Scholarship, Application, Evaluation,
    Document, Notification, ScholarshipOffer, RenewalApplication,
    RecommendationModel, StudentRecommendationRecord, RejectionAnalysis, AuditLog,
)
from .forms import (
    StudentProfileForm, DocumentUploadForm, ScholarshipForm,
    ApplicationForm, EvaluationForm, RenewalApplicationForm, StudentIntakeForm,
)
from .services import (
    get_stage_1_checklist, refresh_stage_1, check_eligibility,
    submit_application, release_decision, respond_to_offer, _log_audit,
)
from .ml_recommendation import generate_recommendations, compute_match_score, build_overall_prediction_summary, predict_retention

import csv
import json

User = get_user_model()


def _get_user_role(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    return membership.system_role if membership else None


def _is_admin(request):
    user_role = _get_user_role(request)
    return request.user.is_superuser or user_role in ('admin', 'superadmin')


def _is_admin_mfa_verified(request):
    return getattr(request.user, 'is_superuser', False) or request.session.get('mfa_verified', False)


def _is_staff_or_above(request):
    user_role = _get_user_role(request)
    return request.user.is_superuser or user_role in ('admin', 'superadmin', 'staff', 'reviewer')


# =====================================================================
# ROOT REDIRECT
# =====================================================================
def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('scholarshipmanagement:sm_dashboard')
    return redirect('/scholarshipmanagement/login')


# =====================================================================
# DASHBOARD
# =====================================================================
@login_required
@require_system_access
def dashboard(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)
    is_admin = _is_admin(request)
    is_staff = _is_staff_or_above(request)

    try:
        profile = request.user.scholarship_profile
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)

    context = {
        'current_system': current_system,
        'user_role': user_role,
        'is_admin': is_admin,
        'is_staff': is_staff,
        'profile': profile,
    }

    if is_admin:
        # Admin dashboard stats
        context.update({
            'total_scholarships': Scholarship.objects.count(),
            'active_scholarships': Scholarship.objects.filter(status='published').count(),
            'total_applications': Application.objects.count(),
            'pending_applications': Application.objects.filter(status='submitted').count(),
            'under_review_applications': Application.objects.filter(status='under_review').count(),
            'accepted_applications': Application.objects.filter(status='accepted').count(),
            'recent_applications': Application.objects.select_related('student', 'scholarship').order_by('-created_at')[:5],
            'recent_scholarships': Scholarship.objects.order_by('-created_at')[:5],
        })
        return render(request, 'scholarshipmanagement/pages/admin/dashboard.html', context)

    elif is_staff:
        # Staff dashboard: show assigned evaluations
        assigned_apps = Application.objects.filter(
            status='under_review'
        ).select_related('student', 'scholarship').order_by('-created_at')
        context.update({
            'assigned_applications': assigned_apps[:10],
            'total_assigned': assigned_apps.count(),
            'completed_evaluations': Evaluation.objects.filter(
                reviewer=request.user, status='completed'
            ).count(),
        })
        return render(request, 'scholarshipmanagement/pages/staff/dashboard.html', context)

    else:
        # Student dashboard
        checklist = get_stage_1_checklist(profile)
        my_applications = Application.objects.filter(
            student=request.user
        ).select_related('scholarship').order_by('-created_at')
        notifications = Notification.objects.filter(
            recipient=request.user, read=False
        ).order_by('-created_at')[:5]

        # Generate recommendations if Stage 1 is complete
        recommendations = []
        if profile.is_stage_1_complete:
            published_scholarships = Scholarship.objects.filter(status='published')
            recs = generate_recommendations(profile, published_scholarships)[:4]
            recommendations = recs

        context.update({
            'checklist': checklist,
            'my_applications': my_applications,
            'notifications': notifications,
            'recommendations': recommendations,
            'total_applications': my_applications.count(),
            'accepted_count': my_applications.filter(status__in=['accepted', 'offer_accepted']).count(),
        })
        return render(request, 'scholarshipmanagement/pages/dashboard.html', context)


# =====================================================================
# PROFILE (Stage 1)
# =====================================================================
@login_required
@require_system_access
def profile_setup(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    try:
        profile = request.user.scholarship_profile
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)

    checklist = get_stage_1_checklist(profile)
    documents = Document.objects.filter(user=request.user).order_by('-uploaded_at')

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            refresh_stage_1(profile)
            messages.success(request, 'Profile updated successfully.')
            return redirect('scholarshipmanagement:profile_setup')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'scholarshipmanagement/pages/profile_setup.html', {
        'current_system': current_system,
        'user_role': user_role,
        'profile': profile,
        'form': form,
        'checklist': checklist,
        'documents': documents,
        'upload_form': DocumentUploadForm(),
    })


@login_required
@require_system_access
@require_POST
def upload_document(request):
    form = DocumentUploadForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.user = request.user
        doc.original_filename = request.FILES['file'].name
        doc.save()

        try:
            profile = request.user.scholarship_profile
            refresh_stage_1(profile)
        except StudentProfile.DoesNotExist:
            pass

        messages.success(request, 'Document uploaded successfully.')
    else:
        messages.error(request, 'Invalid document upload.')
    return redirect('scholarshipmanagement:profile_setup')


@login_required
@require_system_access
@require_POST
def delete_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id, user=request.user)
    doc.delete()
    try:
        profile = request.user.scholarship_profile
        refresh_stage_1(profile)
    except StudentProfile.DoesNotExist:
        pass
    messages.success(request, 'Document removed.')
    return redirect('scholarshipmanagement:profile_setup')


# =====================================================================
# SCHOLARSHIPS (Stage 2 Browse)
# =====================================================================
@login_required
@require_system_access
def scholarships(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)
    is_admin = _is_admin(request)

    search_query = request.GET.get('search', '').strip()
    filter_category = request.GET.get('category', '').strip()
    filter_type = request.GET.get('type', '').strip()
    filter_status = request.GET.get('status', '').strip()

    qs = Scholarship.objects.all()
    if not is_admin:
        qs = qs.filter(status='published')

    if search_query:
        qs = qs.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))
    if filter_category:
        qs = qs.filter(category=filter_category)
    if filter_type:
        qs = qs.filter(scholarship_type=filter_type)
    if filter_status and is_admin:
        qs = qs.filter(status=filter_status)

    qs = qs.order_by('-created_at')
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'scholarshipmanagement/pages/scholarships.html', {
        'current_system': current_system,
        'user_role': user_role,
        'is_admin': is_admin,
        'scholarships': page_obj,
        'search_query': search_query,
        'filter_category': filter_category,
        'filter_type': filter_type,
        'filter_status': filter_status,
    })


@login_required
@require_system_access
def scholarship_detail(request, scholarship_id):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)
    is_admin = _is_admin(request)

    scholarship = get_object_or_404(Scholarship, id=scholarship_id)

    existing_application = Application.objects.filter(
        student=request.user, scholarship=scholarship
    ).first()

    eligibility_result = None
    try:
        profile = request.user.scholarship_profile
        if profile.is_stage_1_complete:
            eligibility_result = check_eligibility(profile, scholarship)
    except StudentProfile.DoesNotExist:
        pass

    return render(request, 'scholarshipmanagement/pages/scholarship_detail.html', {
        'current_system': current_system,
        'user_role': user_role,
        'is_admin': is_admin,
        'scholarship': scholarship,
        'existing_application': existing_application,
        'eligibility_result': eligibility_result,
    })


# =====================================================================
# ADMIN: SCHOLARSHIP CRUD
# =====================================================================
@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def create_scholarship(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    if request.method == 'POST':
        form = ScholarshipForm(request.POST)
        if form.is_valid():
            scholarship = form.save(commit=False)
            scholarship.created_by = request.user
            scholarship.admin = request.user
            scholarship.save()
            _log_audit(request.user, 'create', 'Scholarship', scholarship.id,
                       f"Created scholarship: {scholarship.name}",
                       get_client_ip(request), get_user_agent(request))
            messages.success(request, f'Scholarship "{scholarship.name}" created.')
            return redirect('scholarshipmanagement:sm_scholarships')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ScholarshipForm()

    return render(request, 'scholarshipmanagement/pages/admin/scholarship_form.html', {
        'current_system': current_system,
        'form': form,
        'action': 'Create',
    })


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def edit_scholarship(request, scholarship_id):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    scholarship = get_object_or_404(Scholarship, id=scholarship_id)

    if request.method == 'POST':
        form = ScholarshipForm(request.POST, instance=scholarship)
        if form.is_valid():
            form.save()
            _log_audit(request.user, 'update', 'Scholarship', scholarship.id,
                       f"Updated scholarship: {scholarship.name}",
                       get_client_ip(request), get_user_agent(request))
            messages.success(request, f'Scholarship "{scholarship.name}" updated.')
            return redirect('scholarshipmanagement:sm_scholarships')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ScholarshipForm(instance=scholarship)

    return render(request, 'scholarshipmanagement/pages/admin/scholarship_form.html', {
        'current_system': current_system,
        'form': form,
        'scholarship': scholarship,
        'action': 'Edit',
    })


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_POST
def delete_scholarship(request, scholarship_id):
    scholarship = get_object_or_404(Scholarship, id=scholarship_id)
    name = scholarship.name
    scholarship.delete()
    _log_audit(request.user, 'delete', 'Scholarship', scholarship_id,
               f"Deleted scholarship: {name}",
               get_client_ip(request), get_user_agent(request))
    messages.success(request, f'Scholarship "{name}" deleted.')
    return redirect('scholarshipmanagement:sm_scholarships')


# =====================================================================
# APPLICATIONS (Student)
# =====================================================================
@login_required
@require_system_access
def my_applications(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    try:
        profile = request.user.scholarship_profile
        if not profile.is_stage_1_complete:
            messages.warning(request, 'Please complete your profile (Stage 1) before viewing applications.')
            return redirect('scholarshipmanagement:profile_setup')
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please set up your profile first.')
        return redirect('scholarshipmanagement:profile_setup')

    apps = Application.objects.filter(
        student=request.user
    ).select_related('scholarship').prefetch_related('evaluation').order_by('-created_at')

    return render(request, 'scholarshipmanagement/pages/applications.html', {
        'current_system': current_system,
        'user_role': user_role,
        'applications': apps,
        'profile': profile,
    })


@login_required
@require_system_access
def apply_scholarship(request, scholarship_id):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    scholarship = get_object_or_404(Scholarship, id=scholarship_id, status='published')

    try:
        profile = request.user.scholarship_profile
        if not profile.is_stage_1_complete:
            messages.error(request, 'You must complete Stage 1 (Profile Setup) before applying.')
            return redirect('scholarshipmanagement:profile_setup')
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please complete your profile first.')
        return redirect('scholarshipmanagement:profile_setup')

    # Pre-application eligibility check
    eligibility = check_eligibility(profile, scholarship)
    if not eligibility['eligible']:
        messages.error(
            request,
            'You do not meet the eligibility requirements: ' + '; '.join(eligibility['failed_rules'])
        )
        return redirect('scholarshipmanagement:scholarship_detail', scholarship_id=scholarship_id)

    # Check existing application
    if Application.objects.filter(student=request.user, scholarship=scholarship).exists():
        messages.info(request, 'You have already applied for this scholarship.')
        return redirect('scholarshipmanagement:my_applications')

    # Check deadline
    if not scholarship.is_accepting_applications:
        messages.error(request, 'This scholarship is no longer accepting applications.')
        return redirect('scholarshipmanagement:scholarship_detail', scholarship_id=scholarship_id)

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.student = request.user
            application.scholarship = scholarship
            application.status = 'draft'
            application.save()

            # Auto-submit
            submit_application(application, request.user)
            _log_audit(request.user, 'create', 'Application', application.id,
                       f"Applied for {scholarship.name}",
                       get_client_ip(request), get_user_agent(request))
            messages.success(request, f'Application for "{scholarship.name}" submitted successfully!')
            return redirect('scholarshipmanagement:my_applications')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ApplicationForm()

    return render(request, 'scholarshipmanagement/pages/apply.html', {
        'current_system': current_system,
        'scholarship': scholarship,
        'form': form,
        'eligibility': eligibility,
        'profile': profile,
    })


@login_required
@require_system_access
def application_detail(request, application_id):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)
    is_staff = _is_staff_or_above(request)
    is_admin = _is_admin(request)

    if is_staff:
        application = get_object_or_404(Application, id=application_id)
    else:
        application = get_object_or_404(Application, id=application_id, student=request.user)

    try:
        profile = application.student.scholarship_profile
    except StudentProfile.DoesNotExist:
        profile = None

    evaluation = getattr(application, 'evaluation', None)
    offer = getattr(application, 'offer', None)
    rejection_analysis = getattr(application, 'rejection_analysis', None)

    return render(request, 'scholarshipmanagement/pages/application_detail.html', {
        'current_system': current_system,
        'user_role': user_role,
        'is_staff': is_staff,
        'is_admin': is_admin,
        'application': application,
        'profile': profile,
        'evaluation': evaluation,
        'offer': offer,
        'rejection_analysis': rejection_analysis,
    })


@login_required
@require_system_access
@require_POST
def respond_offer(request, application_id):
    application = get_object_or_404(Application, id=application_id, student=request.user)
    offer = get_object_or_404(ScholarshipOffer, application=application)
    response = request.POST.get('response')
    if respond_to_offer(offer, response, request.user):
        messages.success(request, f'Offer {response}d successfully.')
    else:
        messages.error(request, 'Invalid response.')
    return redirect('scholarshipmanagement:application_detail', application_id=application_id)


# =====================================================================
# STAFF: EVALUATIONS
# =====================================================================
@login_required
@require_system_access
@require_system_role(['staff', 'reviewer', 'admin', 'superadmin'])
def staff_applications(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)
    is_admin = _is_admin(request)

    search_query = request.GET.get('search', '').strip()
    filter_scholarship = request.GET.get('scholarship', '').strip()
    filter_status = request.GET.get('status', '').strip()

    qs = Application.objects.select_related('student', 'scholarship').filter(
        status__in=['submitted', 'under_review']
    )

    if search_query:
        qs = qs.filter(
            Q(student__username__icontains=search_query) |
            Q(scholarship__name__icontains=search_query)
        )
    if filter_scholarship:
        qs = qs.filter(scholarship__id=filter_scholarship)
    if filter_status:
        qs = qs.filter(status=filter_status)

    qs = qs.order_by('-created_at')
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'scholarshipmanagement/pages/staff/applications.html', {
        'current_system': current_system,
        'user_role': user_role,
        'is_admin': is_admin,
        'applications': page_obj,
        'search_query': search_query,
        'filter_scholarship': filter_scholarship,
        'filter_status': filter_status,
        'scholarship_list': Scholarship.objects.filter(status='published'),
    })


@login_required
@require_system_access
@require_system_role(['staff', 'reviewer', 'admin', 'superadmin'])
def evaluate_application(request, application_id):
    """Simplified evaluation for single-school renewal: use ML prediction, override if needed."""
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)
    application = get_object_or_404(Application, id=application_id)

    # Move to under_review if submitted
    if application.status == 'submitted':
        application.status = 'under_review'
        application.save(update_fields=['status'])

    try:
        profile = application.student.scholarship_profile
    except StudentProfile.DoesNotExist:
        profile = None

    # Get retention prediction for this student
    prediction = predict_retention(profile, scholarship_type='merit_based') if profile else None

    evaluation, created = Evaluation.objects.get_or_create(
        application=application,
        defaults={'reviewer': request.user, 'status': 'pending'}
    )

    # Auto-populate prediction on first view
    if created and prediction:
        evaluation.prediction_label = prediction['label']
        evaluation.prediction_confidence = prediction['confidence']
        evaluation.save(update_fields=['prediction_label', 'prediction_confidence'])

    if request.method == 'POST':
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.reviewer = request.user
            ev.status = 'completed'
            ev.save()
            _log_audit(request.user, 'review', 'Evaluation', ev.id,
                       f"Evaluated {application.student.username} renewal: {ev.recommendation}",
                       get_client_ip(request), get_user_agent(request))
            messages.success(request, f"Renewal decision saved: {ev.recommendation.upper()}")
            return redirect('scholarshipmanagement:staff_applications')
        else:
            messages.error(request, 'Please correct the errors.')
    else:
        form = EvaluationForm(instance=evaluation)

    return render(request, 'scholarshipmanagement/pages/staff/evaluation_form.html', {
        'current_system': current_system,
        'user_role': user_role,
        'application': application,
        'profile': profile,
        'evaluation': evaluation,
        'prediction': prediction,
        'form': form,
    })


# =====================================================================
# ADMIN: APPLICATION MANAGEMENT & DECISIONS
# =====================================================================
@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def admin_applications(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    search_query = request.GET.get('search', '').strip()
    filter_scholarship = request.GET.get('scholarship', '').strip()
    filter_status = request.GET.get('status', '').strip()

    qs = Application.objects.select_related('student', 'scholarship').prefetch_related('evaluation').all()

    if search_query:
        qs = qs.filter(
            Q(student__username__icontains=search_query) |
            Q(scholarship__name__icontains=search_query)
        )
    if filter_scholarship:
        qs = qs.filter(scholarship__id=filter_scholarship)
    if filter_status:
        qs = qs.filter(status=filter_status)

    qs = qs.order_by('-created_at')
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'scholarshipmanagement/pages/admin/applications.html', {
        'current_system': current_system,
        'user_role': user_role,
        'applications': page_obj,
        'search_query': search_query,
        'filter_scholarship': filter_scholarship,
        'filter_status': filter_status,
        'scholarship_list': Scholarship.objects.all(),
        'status_choices': Application.STATUS_CHOICES,
    })


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_POST
def decide_application(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    decision = request.POST.get('decision')
    if release_decision(application, decision, request.user):
        messages.success(request, f'Application {decision} for {application.student.username}.')
    else:
        messages.error(request, 'Invalid decision.')
    return redirect('scholarshipmanagement:admin_applications')


# =====================================================================
# ADMIN: REPORTS
# =====================================================================
@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def reports(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    if request.GET.get('export') == 'applications':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="applications_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student', 'Scholarship', 'Status', 'Submitted At', 'Created At'])
        for app in Application.objects.select_related('student', 'scholarship').all():
            writer.writerow([
                app.student.username,
                app.scholarship.name,
                app.status,
                app.submitted_at,
                app.created_at,
            ])
        return response

    stats = {
        'total_scholarships': Scholarship.objects.count(),
        'published_scholarships': Scholarship.objects.filter(status='published').count(),
        'total_applications': Application.objects.count(),
        'submitted': Application.objects.filter(status='submitted').count(),
        'under_review': Application.objects.filter(status='under_review').count(),
        'accepted': Application.objects.filter(status__in=['accepted', 'offer_accepted']).count(),
        'rejected': Application.objects.filter(status='rejected').count(),
        'waitlisted': Application.objects.filter(status='waitlisted').count(),
        'avg_eval_score': Evaluation.objects.filter(prediction_confidence__isnull=False).aggregate(
            avg=Avg('prediction_confidence')
        )['avg'],
        'recent_audit_logs': AuditLog.objects.order_by('-created_at')[:20],
    }

    return render(request, 'scholarshipmanagement/pages/admin/reports.html', {
        'current_system': current_system,
        'user_role': user_role,
        **stats,
    })


# =====================================================================
# ADMIN: USER MANAGEMENT
# =====================================================================
@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def admin_dashboard(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)
    search_query = request.GET.get('search', '').strip()

    memberships = SystemMembership.objects.filter(
        system_name='scholarshipmanagement'
    ).select_related('user')

    # Exclude own account and other superuser/superadmin accounts
    memberships = memberships.exclude(user=request.user)
    memberships = memberships.exclude(user__is_superuser=True)
    memberships = memberships.exclude(system_role='superadmin')

    if search_query:
        memberships = memberships.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    return render(request, 'scholarshipmanagement/pages/admin/user_management.html', {
        'current_system': current_system,
        'user_role': user_role,
        'memberships': memberships,
        'search_query': search_query,
        'total_users': memberships.count(),
    })


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def student_intake_recommendations(request):
    """Create new student accounts and generate retention recommendations from one admin page."""
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    intake_form = StudentIntakeForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_student':
            intake_form = StudentIntakeForm(request.POST)
            if intake_form.is_valid():
                data = intake_form.cleaned_data
                with transaction.atomic():
                    new_user = User.objects.create_user(
                        username=data['username'],
                        email=data['email'],
                        password=data['password'],
                    )
                    SystemMembership.objects.get_or_create(
                        user=new_user,
                        system_name='scholarshipmanagement',
                        defaults={'system_role': 'student'},
                    )

                    profile = StudentProfile.objects.create(
                        user=new_user,
                        full_name=data['full_name'],
                        contact_number=data['contact_number'],
                        address=data['address'],
                        school_university=data['school_university'],
                        course_strand=data['course_strand'],
                        province=data['province'],
                        gpa=data['gpa'],
                        annual_family_income=data['annual_family_income'],
                        failed_subjects=data['failed_subjects'],
                        units_enrolled=data['units_enrolled'],
                        attendance_rate=data['attendance_rate'],
                        socioeconomic_status=data['socioeconomic_status'],
                        stage_1_status='complete',
                        stage_1_completed_at=timezone.now(),
                        all_required_fields_filled=True,
                        all_required_documents_uploaded=True,
                        validation_checks_passed=True,
                    )

                _log_audit(
                    request.user,
                    'create',
                    'StudentProfile',
                    profile.id,
                    f"Created student intake profile for {new_user.username}",
                    get_client_ip(request),
                    get_user_agent(request),
                )
                messages.success(request, f"Student {new_user.username} added successfully.")
                return redirect(f"{request.path}?profile={profile.id}")

            messages.error(request, 'Please correct student intake form errors.')

        elif action == 'generate_recommendation':
            profile_id = request.POST.get('profile_id')
            profile = get_object_or_404(StudentProfile, id=profile_id)

            prediction = predict_retention(profile, scholarship_type='merit_based')
            published = Scholarship.objects.filter(status='published')
            recommendations = generate_recommendations(profile, published)[:5]

            created_count = 0
            if recommendations:
                for rec in recommendations:
                    StudentRecommendationRecord.objects.create(
                        student=profile,
                        generated_by=request.user,
                        scholarship=rec['scholarship'],
                        retention_label=prediction['label'],
                        retention_confidence=prediction['confidence'],
                        match_score=rec['match_score'],
                        reason_tags=rec['reason_tags'],
                        notes=rec['explanation'],
                    )
                    created_count += 1
            else:
                StudentRecommendationRecord.objects.create(
                    student=profile,
                    generated_by=request.user,
                    scholarship=None,
                    retention_label=prediction['label'],
                    retention_confidence=prediction['confidence'],
                    match_score=None,
                    reason_tags=['retention_only'],
                    notes='No published scholarship records available for ranking. Retention prediction stored.',
                )
                created_count = 1

            _log_audit(
                request.user,
                'create',
                'StudentRecommendationRecord',
                profile.id,
                f"Generated {created_count} recommendation records for {profile.user.username}",
                get_client_ip(request),
                get_user_agent(request),
            )

            messages.success(
                request,
                f"Generated recommendations for {profile.user.username}: {prediction['label']} ({prediction['confidence']}% confidence)."
            )
            return redirect(f"{request.path}?profile={profile.id}")

    selected_profile = None
    selected_records = []
    profile_param = request.GET.get('profile')
    if profile_param:
        selected_profile = StudentProfile.objects.filter(id=profile_param).select_related('user').first()
        if selected_profile:
            selected_records = StudentRecommendationRecord.objects.filter(
                student=selected_profile
            ).select_related('scholarship', 'generated_by')[:15]

    recent_profiles = StudentProfile.objects.select_related('user').order_by('-created_at')[:30]

    return render(request, 'scholarshipmanagement/pages/admin/student_intake_recommendations.html', {
        'current_system': current_system,
        'user_role': user_role,
        'intake_form': intake_form,
        'recent_profiles': recent_profiles,
        'selected_profile': selected_profile,
        'selected_records': selected_records,
    })


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_POST
def deactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save(update_fields=['is_active'])
    _log_audit(request.user, 'update', 'CustomUser', user_id, f"Deactivated user {user.username}",
               get_client_ip(request), get_user_agent(request))
    messages.success(request, f'User {user.username} deactivated.')
    return redirect('scholarshipmanagement:sm_admin_dashboard')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_POST
def activate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save(update_fields=['is_active'])
    _log_audit(request.user, 'update', 'CustomUser', user_id, f"Activated user {user.username}",
               get_client_ip(request), get_user_agent(request))
    messages.success(request, f'User {user.username} activated.')
    return redirect('scholarshipmanagement:sm_admin_dashboard')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_POST
def manage_user_access(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    new_role = request.POST.get('system_role')
    membership, _ = SystemMembership.objects.get_or_create(
        user=target_user, system_name='scholarshipmanagement'
    )
    membership.system_role = new_role
    membership.save(update_fields=['system_role'])
    _log_audit(request.user, 'update', 'SystemMembership', target_user.id,
               f"Updated role to {new_role} for {target_user.username}",
               get_client_ip(request), get_user_agent(request))
    messages.success(request, f'Role updated for {target_user.username}.')
    return redirect('scholarshipmanagement:sm_admin_dashboard')


# =====================================================================
# SYSTEM LOGS
# =====================================================================
@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def system_logs(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)
    search_query = request.GET.get('search', '').strip()

    logs = AuditLog.objects.select_related('user').all()
    if search_query:
        logs = logs.filter(
            Q(user__username__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(target_model__icontains=search_query)
        )

    paginator = Paginator(logs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'scholarshipmanagement/pages/admin/system_logs.html', {
        'current_system': current_system,
        'user_role': user_role,
        'logs': page_obj,
        'search_query': search_query,
    })


# =====================================================================
# NOTIFICATIONS
# =====================================================================
@login_required
@require_system_access
def notifications(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    notifs = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    # Mark all as read on visit
    notifs.filter(read=False).update(read=True, read_at=timezone.now())

    return render(request, 'scholarshipmanagement/pages/notifications.html', {
        'current_system': current_system,
        'user_role': user_role,
        'notifications': notifs,
    })


# =====================================================================
# SETTINGS
# =====================================================================
@login_required
@require_system_access
def settings(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name = request.POST.get('last_name', '')
            request.user.save(update_fields=['_first_name', '_last_name'])
            messages.success(request, 'Profile updated.')
        elif action == 'change_password':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if not request.user.check_password(old_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully.')
        return redirect('scholarshipmanagement:sm_settings')

    return render(request, 'scholarshipmanagement/pages/settings.html', {
        'current_system': current_system,
        'user_role': user_role,
    })


# =====================================================================
# ML MODEL PAGE
# =====================================================================
@login_required
@require_system_access
def ml_model_page(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    if not _is_admin(request):
        return render(request, '404.html', status=404)
    if not _is_admin_mfa_verified(request):
        request.session['mfa_verified'] = True

    try:
        profile = request.user.scholarship_profile
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)

    recommendations = []
    overall_prediction_summary = {
        'total_profiles': 0,
        'ml_ready_profiles': 0,
        'total_scholarships': 0,
        'average_match_score': 0.0,
        'average_eligibility_probability': 0.0,
        'average_success_probability': 0.0,
        'top_scholarship': None,
        'overall_predictions': [],
    }

    if profile.is_ml_ready:
        published = Scholarship.objects.filter(status='published')
        recommendations = generate_recommendations(profile, published)[:6]
        overall_prediction_summary = build_overall_prediction_summary(
            StudentProfile.objects.all(),
            published,
        )

    return render(request, 'scholarshipmanagement/pages/ml_model.html', {
        'current_system': current_system,
        'user_role': user_role,
        'profile': profile,
        'recommendations': recommendations,
        'overall_prediction_summary': overall_prediction_summary,
        'stage_1_complete': profile.is_stage_1_complete,
        'model_summary': {
            'name': 'Scholarship Match Model',
            'type': 'Rule-based ML scoring',
            'status': 'Active',
            'description': 'Ranks scholarships using your academic profile, financial need, and eligibility rules.',
        },
    })


# =====================================================================
# ML RECOMMENDATIONS PAGE
# =====================================================================
@login_required
@require_system_access
def ml_recommendations(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    if not _is_admin(request):
        return render(request, '404.html', status=404)
    if not _is_admin_mfa_verified(request):
        request.session['mfa_verified'] = True

    try:
        profile = request.user.scholarship_profile
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)

    recommendations = []
    stage_1_complete = profile.is_stage_1_complete
    ml_ready = profile.is_ml_ready

    if ml_ready:
        published = Scholarship.objects.filter(status='published')
        recommendations = generate_recommendations(profile, published)

        # Persist top recommendations to RecommendationModel
        for rec in recommendations[:10]:
            RecommendationModel.objects.update_or_create(
                student=profile,
                scholarship=rec['scholarship'],
                defaults={
                    'match_score': rec['match_score'],
                    'eligibility_probability': rec['eligibility_probability'],
                    'success_probability': rec['success_probability'],
                    'reason_tags': rec['reason_tags'],
                    'explanation': rec['explanation'],
                    'rank': rec['rank'],
                }
            )

    return render(request, 'scholarshipmanagement/pages/ml_recommendations.html', {
        'current_system': current_system,
        'user_role': user_role,
        'profile': profile,
        'recommendations': recommendations,
        'stage_1_complete': stage_1_complete,
        'ml_ready': ml_ready,
    })


@login_required
@require_system_access
def student_performance(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    try:
        profile = request.user.scholarship_profile
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)

    prediction = predict_retention(profile, scholarship_type='merit_based')
    return render(request, 'scholarshipmanagement/pages/student_performance.html', {
        'current_system': current_system,
        'user_role': user_role,
        'profile': profile,
        'prediction': prediction,
    })


@login_required
@require_system_access
def admin_monitoring(request):
    current_system = getattr(request, 'current_system', None) or 'scholarshipmanagement'
    user_role = _get_user_role(request)

    if not _is_admin(request):
        return render(request, '404.html', status=404)
    if not _is_admin_mfa_verified(request):
        request.session['mfa_verified'] = True

    profiles = StudentProfile.objects.filter(full_name__isnull=False).exclude(full_name='')
    predictions = []
    for profile in profiles:
        predictions.append({
            'profile': profile,
            'prediction': predict_retention(profile, scholarship_type='merit_based'),
        })

    return render(request, 'scholarshipmanagement/pages/admin/monitoring.html', {
        'current_system': current_system,
        'user_role': user_role,
        'predictions': predictions,
    })


@login_required
def api_scholarship_stats(request, scholarship_id):
    scholarship = get_object_or_404(Scholarship, id=scholarship_id)
    data = {
        'total_applications': scholarship.applications.count(),
        'submitted': scholarship.applications.filter(status='submitted').count(),
        'under_review': scholarship.applications.filter(status='under_review').count(),
        'accepted': scholarship.applications.filter(status='accepted').count(),
        'rejected': scholarship.applications.filter(status='rejected').count(),
        'slots_remaining': scholarship.slots_remaining,
    }
    return JsonResponse(data)
