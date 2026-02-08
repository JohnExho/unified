from django.http import Http404, JsonResponse, HttpResponse
from django.views.defaults import page_not_found
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField, Prefetch
from django.db.models.functions import TruncWeek
from django.db import IntegrityError, transaction
from decimal import Decimal, ROUND_HALF_UP
from .models import (
    EvaluationCriterion, EvaluationCategory, 
    AcademicTerm, EvaluationCycle, Rubric, Department, UserDepartmentAssignment, EvaluationForm,
    Evaluation, EvaluationScore, EvaluationComment, ComputedResult, Recommendation
)
from core.decorators import require_system_access, require_system_role
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from core.models import Logs, SystemMembership, Systems, Address
from core.utils import encrypt, decrypt, get_client_ip, get_user_agent
from django.core.paginator import Paginator
import json
from datetime import datetime, timedelta
import uuid


@login_required
@require_system_access
@require_system_role(['user', 'instructor', 'superadmin'])
def dashboard(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    user = request.user
    
    # Check if user is admin/superadmin in this system
    is_admin = user.systemmembership_set.filter(
        system_name=current_system,
        system_role__in=['admin', 'superadmin']
    ).exists()
    
    # Get statistics and evaluations based on role
    if is_admin:
        # Admin sees all computed results, matching Results & Analytics.
        result_scope = ComputedResult.objects.all()
        evaluation_scope = Evaluation.objects.all()

        total_teachers = result_scope.values('evaluatee').distinct().count()

        # Pending evaluations reflect active forms (open cycles).
        pending_evaluations = EvaluationForm.objects.filter(
            is_active=True,
            cycle__is_closed=False,
        ).count()

        all_results = result_scope
        
        if all_results.exists():
            avg_score = all_results.aggregate(
                avg=Avg('total_score')
            )['avg'] or 0
            avg_score = round(float(avg_score), 1)
        else:
            avg_score = 0
        
        high_performers = all_results.filter(
            Q(performance_level__iexact='very high')
            | Q(performance_level__iexact='high')
        ).count()

        high_performer_percent = round((high_performers / total_teachers) * 100, 1) if total_teachers else 0
        
        # Recent evaluations (all submitted ones)
        recent_evaluations = evaluation_scope.filter(
            is_submitted=True
        ).select_related('evaluatee', 'form__cycle').order_by('-submitted_at')[:5]
        
        # Recent results
        recent_results = result_scope.select_related(
            'evaluatee', 'cycle'
        ).order_by('-computed_at')[:5]
        
    else:
        # Regular user sees only their own data
        # Pending evaluations they received
        pending_evaluations = Evaluation.objects.filter(
            evaluatee=user,
            is_submitted=False
        ).count()
        
        # Their computed results
        user_results = ComputedResult.objects.filter(evaluatee=user)
        
        if user_results.exists():
            avg_score = user_results.aggregate(
                avg=Avg('total_score')
            )['avg'] or 0
            avg_score = round(float(avg_score), 1)
        else:
            avg_score = 0
        
        # High performance results for this user
        high_performers = user_results.filter(
            performance_level__in=['Very High', 'High']
        ).count()

        high_performer_percent = None
        
        total_teachers = 1  # Just themselves
        
        # Their recent evaluations received
        recent_evaluations = Evaluation.objects.filter(
            evaluatee=user,
            is_submitted=True
        ).select_related('evaluator', 'form__cycle').order_by('-submitted_at')[:5]
        
        # Their recent results
        recent_results = user_results.select_related(
            'cycle'
        ).order_by('-computed_at')[:5]
    
    # Build recent evaluations data for template
    evaluations_data = []
    for eval_obj in recent_evaluations:
        evaluations_data.append({
            'evaluator': eval_obj.evaluator.get_full_name() if eval_obj.evaluator else 'System',
            'evaluatee': eval_obj.evaluatee.get_full_name(),
            'cycle': f"{eval_obj.form.cycle.term.name} - {eval_obj.form.cycle.name}",
            'submitted_at': eval_obj.submitted_at,
        })
    
    # Build recent results data
    results_data = []
    for result in recent_results:
        results_data.append({
            'evaluatee': result.evaluatee.get_full_name(),
            'cycle': f"{result.cycle.term.name} - {result.cycle.name}",
            'performance_level': result.performance_level,
            'total_score': f"{result.total_score:.1f}",
            'computed_at': result.computed_at,
        })
    
    # Get recommendations if user
    if not is_admin and user_results.exists():
        recommendations = Recommendation.objects.filter(
            result__evaluatee=user
        ).select_related('result__cycle').order_by('-created_at')[:5]
    elif is_admin:
        recommendations = Recommendation.objects.select_related(
            'result__evaluatee', 'result__cycle'
        ).order_by('-created_at')[:5]
    else:
        recommendations = []

    # Build trend chart data from computed results
    if is_admin:
        trend_source = result_scope
        dept_source = result_scope.filter(
            evaluatee__userdepartmentassignment__department__is_active=True
        )
    else:
        trend_source = user_results
        dept_source = ComputedResult.objects.filter(
            evaluatee=user,
            evaluatee__userdepartmentassignment__department__is_active=True
        )

    trend_rows = (
        trend_source.annotate(week=TruncWeek('computed_at'))
        .values('week')
        .annotate(avg_score=Avg('total_score'))
        .order_by('week')
    )
    trend_labels = [row['week'].strftime('%b %d') if row['week'] else '' for row in trend_rows]
    trend_values = [round(float(row['avg_score'] or 0), 2) for row in trend_rows]

    dept_rows = (
        dept_source.values('evaluatee__userdepartmentassignment__department__name')
        .annotate(avg_score=Avg('total_score'))
        .order_by('-avg_score')
    )
    dept_labels = [row['evaluatee__userdepartmentassignment__department__name'] for row in dept_rows]
    dept_values = [round(float(row['avg_score'] or 0), 2) for row in dept_rows]
    
    # Build recent recommendations data
    recommendations_data = []
    for rec in recommendations:
        recommendations_data.append({
            'evaluatee': rec.result.evaluatee.get_full_name(),
            'cycle': f"{rec.result.cycle.term.name} - {rec.result.cycle.name}",
            'type': rec.get_recommendation_type_display(),
            'description': rec.description,
            'created_at': rec.created_at,
        })
    
    # Get pending evaluations for the user (if they're an evaluator)
    if not is_admin:
        pending_to_submit = Evaluation.objects.filter(
            evaluator=user,
            is_submitted=False
        ).select_related('evaluatee', 'form__cycle')[:5]
    else:
        pending_to_submit = evaluation_scope.filter(
            is_submitted=False
        ).select_related('evaluator', 'evaluatee', 'form__cycle')[:5]
    
    context = {
        'systems': systems,
        'current_system': current_system,
        'is_admin': is_admin,
        'total_teachers': total_teachers,
        'pending_evaluations': pending_evaluations,
        'avg_score': avg_score,
        'high_performers': high_performers,
        'high_performer_percent': high_performer_percent,
        'recent_evaluations': evaluations_data,
        'recent_results': results_data,
        'recent_recommendations': recommendations_data,
        'pending_to_submit': pending_to_submit,
        'trend_chart_json': json.dumps({'labels': trend_labels, 'values': trend_values}),
        'dept_chart_json': json.dumps({'labels': dept_labels, 'values': dept_values}),
    }
    
    return render(request, 'performanceevaluation/pages/dashboard.html', context)


@login_required
@require_system_access
@require_system_role(['user', 'instructor', 'admin', 'superadmin'])
def user_evaluations(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    user = request.user
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', '').strip() or 'cycle'

    membership_role = SystemMembership.objects.filter(
        user=user,
        system_name=current_system,
    ).values_list('system_role', flat=True).first()

    role_forms_map = {
        'user': ['student', 'self'],
        'instructor': ['peer', 'self'],
        'admin': ['supervisor', 'self'],
    }
    allowed_form_types = role_forms_map.get(membership_role, ['self'])
    if user.is_superuser or membership_role == 'superadmin':
        allowed_form_types = ['self', 'student', 'peer', 'supervisor']

    active_forms = EvaluationForm.objects.filter(
        is_active=True,
        cycle__is_closed=False,
    ).select_related('cycle', 'cycle__term').order_by('-cycle__start_date')

    active_forms = active_forms.filter(evaluator_type__in=allowed_form_types)

    if search_query:
        active_forms = active_forms.filter(
            Q(cycle__name__icontains=search_query)
            | Q(cycle__term__name__icontains=search_query)
            | Q(evaluator_type__icontains=search_query)
        )

    sort_map = {
        'cycle': 'cycle__start_date',
        'term': 'cycle__term__start_date',
        'type': 'evaluator_type',
    }
    sort_field = sort_map.get(sort_by, 'cycle__start_date')
    active_forms = active_forms.order_by(sort_field)

    department_ids = UserDepartmentAssignment.objects.filter(
        user=user
    ).values_list('department_id', flat=True)

    evaluatees = get_user_model().objects.filter(
        userdepartmentassignment__department_id__in=department_ids,
    ).filter(
        systemmembership__system_name='performanceevaluation',
        systemmembership__system_role__in=['user', 'instructor', 'admin', 'superadmin'],
    ).exclude(id=user.id).exclude(is_superuser=True).distinct().order_by('username')

    context = {
        'systems': systems,
        'current_system': current_system,
        'active_forms': active_forms,
        'evaluatees': evaluatees,
        'current_user': user,
        'search_query': search_query,
        'sort_by': sort_by,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        forms_html = render_to_string(
            'performanceevaluation/partials/user/_evaluations_forms_list.html',
            context,
            request=request,
        )
        return JsonResponse({'evaluations_forms_html': forms_html})

    return render(request, 'performanceevaluation/pages/evaluations.html', context)


@login_required
@require_system_access
@require_system_role(['user', 'instructor', 'admin', 'superadmin'])
@require_http_methods(["GET", "POST"])
def user_evaluation_form(request, form_id):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    user = request.user

    evaluation_form = get_object_or_404(
        EvaluationForm,
        id=form_id,
        is_active=True,
        cycle__is_closed=False,
    )

    membership_role = SystemMembership.objects.filter(
        user=user,
        system_name=current_system,
    ).values_list('system_role', flat=True).first()

    role_forms_map = {
        'user': ['student', 'self'],
        'instructor': ['peer', 'self'],
        'admin': ['supervisor', 'self'],
    }
    allowed_form_types = role_forms_map.get(membership_role, ['self'])
    if user.is_superuser or membership_role == 'superadmin':
        allowed_form_types = ['self', 'student', 'peer', 'supervisor']

    if evaluation_form.evaluator_type not in allowed_form_types:
        messages.error(request, 'You do not have access to this evaluation form.')
        return redirect('performanceevaluation:user_evaluations')

    if evaluation_form.evaluator_type == 'peer' and membership_role != 'instructor' and not user.is_superuser:
        messages.error(request, 'Peer evaluations are only available to instructors.')
        return redirect('performanceevaluation:user_evaluations')

    department_ids = UserDepartmentAssignment.objects.filter(
        user=user
    ).values_list('department_id', flat=True)

    allowed_evaluatees = get_user_model().objects.filter(
        userdepartmentassignment__department_id__in=department_ids,
    ).filter(
        systemmembership__system_name='performanceevaluation',
        systemmembership__system_role__in=['user', 'instructor', 'admin', 'superadmin'],
    ).exclude(id=user.id).exclude(is_superuser=True).distinct()

    evaluatee_id = request.POST.get('evaluatee') or request.GET.get('evaluatee')
    if evaluation_form.evaluator_type == 'self':
        evaluatee_id = str(user.id)

    if not evaluatee_id:
        messages.error(request, 'Please select an evaluatee before opening the form.')
        return redirect('performanceevaluation:user_evaluations')

    evaluatee = get_object_or_404(allowed_evaluatees, id=evaluatee_id)

    rubric_prefetch = Prefetch('rubric_set', queryset=Rubric.objects.order_by('level'))
    criteria_prefetch = Prefetch(
        'evaluationcriterion_set',
        queryset=EvaluationCriterion.objects.order_by('name').prefetch_related(rubric_prefetch),
    )

    categories = EvaluationCategory.objects.filter(
        cycle=evaluation_form.cycle
    ).order_by('name').prefetch_related(criteria_prefetch)

    if request.method == 'POST':
        criteria = EvaluationCriterion.objects.filter(category__cycle=evaluation_form.cycle)
        score_rows = []

        for criterion in criteria:
            key = f"criterion_{criterion.id}"
            value = request.POST.get(key)
            if not value:
                messages.error(request, 'Please answer all required questions.')
                return redirect(request.path + f"?evaluatee={evaluatee_id}")
            try:
                score_value = int(value)
            except (TypeError, ValueError):
                messages.error(request, 'Invalid score provided.')
                return redirect(request.path + f"?evaluatee={evaluatee_id}")
            score_rows.append((criterion, score_value))

        comment_text = request.POST.get('overall_comment', '').strip()

        with transaction.atomic():
            evaluation = Evaluation.objects.create(
                form=evaluation_form,
                evaluatee=evaluatee,
                evaluator=user,
                submitted_at=timezone.now(),
                is_submitted=True,
            )

            EvaluationScore.objects.bulk_create([
                EvaluationScore(evaluation=evaluation, criterion=criterion, score=score)
                for criterion, score in score_rows
            ])

            if comment_text:
                EvaluationComment.objects.create(
                    evaluation=evaluation,
                    comment=comment_text,
                )

        messages.success(request, 'Evaluation submitted successfully.')
        return redirect('performanceevaluation:user_evaluations')

    context = {
        'systems': systems,
        'current_system': current_system,
        'evaluation_form': evaluation_form,
        'evaluatee': evaluatee,
        'categories': categories,
    }

    return render(request, 'performanceevaluation/pages/evaluation_form.html', context)


@login_required
@require_system_access
@require_system_role(['user', 'instructor', 'admin', 'superadmin'])
def user_results_analytics(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    user = request.user

    search_query = request.GET.get('search', '').strip()
    cycle_filter = request.GET.get('cycle', '').strip()

    evaluations_qs = Evaluation.objects.filter(
        evaluator=user,
        is_submitted=True,
    ).select_related(
        'evaluatee',
        'form',
        'form__cycle',
        'form__cycle__term',
    )

    if search_query:
        evaluations_qs = evaluations_qs.filter(
            Q(evaluatee__username__icontains=search_query)
            | Q(evaluatee__email__icontains=search_query)
        )

    if cycle_filter:
        evaluations_qs = evaluations_qs.filter(form__cycle_id=cycle_filter)

    evaluations_qs = evaluations_qs.order_by('-submitted_at')

    cycles = EvaluationCycle.objects.select_related('term').order_by('-start_date')

    context = {
        'systems': systems,
        'current_system': current_system,
        'search_query': search_query,
        'cycle_filter': cycle_filter,
        'evaluations': evaluations_qs,
        'cycles': cycles,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        table_html = render_to_string(
            'performanceevaluation/partials/user/_user_results_analytics_table.html',
            context,
            request=request,
        )
        return JsonResponse({'user_results_table_html': table_html})

    return render(request, 'performanceevaluation/pages/user_results_analytics.html', context)


@login_required
@require_system_access
@require_system_role(['user', 'instructor', 'admin', 'superadmin'])
def user_evaluation_review(request, evaluation_id):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    user = request.user

    evaluation = get_object_or_404(
        Evaluation.objects.select_related(
            'evaluatee',
            'evaluator',
            'form',
            'form__cycle',
            'form__cycle__term',
        ),
        id=evaluation_id,
        is_submitted=True,
    )

    if evaluation.evaluator_id != user.id and not user.is_superuser:
        raise Http404

    categories = EvaluationCategory.objects.filter(
        cycle=evaluation.form.cycle
    ).prefetch_related('evaluationcriterion_set__rubric_set')

    score_map = {
        score.criterion_id: str(score.score)
        for score in EvaluationScore.objects.filter(evaluation=evaluation)
    }
    comment = EvaluationComment.objects.filter(evaluation=evaluation).first()

    category_rows = []
    for category in categories:
        criteria_rows = []
        for criterion in category.evaluationcriterion_set.all():
            criteria_rows.append({
                'criterion': criterion,
                'rubrics': list(criterion.rubric_set.all()),
                'selected_score': score_map.get(criterion.id, ''),
            })
        category_rows.append({
            'category': category,
            'criteria': criteria_rows,
        })

    context = {
        'systems': systems,
        'current_system': current_system,
        'evaluation': evaluation,
        'evaluatee': evaluation.evaluatee,
        'evaluation_form': evaluation.form,
        'categories': category_rows,
        'comment': comment.comment if comment else '',
    }

    return render(request, 'performanceevaluation/pages/user_evaluation_review.html', context)


@login_required
@require_system_access
def settings(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])

    home_address = Address.objects.filter(user=request.user, type='home').first()
    secondary_address = Address.objects.filter(user=request.user, type='billing').first()

    if home_address:
        home_address.full_address = decrypt(home_address.full_address)
        home_address.city = decrypt(home_address.city)
        home_address.province = decrypt(home_address.province)
        home_address.postal_code = decrypt(home_address.postal_code)
        home_address.country = decrypt(home_address.country)

    if secondary_address:
        secondary_address.full_address = decrypt(secondary_address.full_address)
        secondary_address.city = decrypt(secondary_address.city)
        secondary_address.province = decrypt(secondary_address.province)
        secondary_address.postal_code = decrypt(secondary_address.postal_code)
        secondary_address.country = decrypt(secondary_address.country)

    return render(request, 'performanceevaluation/pages/settings.html', {
        'systems': systems,
        'current_system': current_system,
        'home_address': home_address,
        'secondary_address': secondary_address,
    })


@login_required
@require_POST
def upload_avatar(request):
    avatar = request.FILES.get("avatar")
    if avatar:
        if request.user.avatar:
            request.user.avatar.delete(save=False)

        request.user.avatar = avatar
        request.user.save()

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='User',
            target_id=request.user.id,
            description=f"Updated avatar for user '{request.user.username}'",
            hidden_description=f"User '{request.user.username}' updated their avatar",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, "Avatar uploaded successfully.")
    return redirect('performanceevaluation:settings')


@login_required
@require_POST
def remove_avatar(request):
    if request.user.avatar:
        request.user.avatar.delete(save=False)
        request.user.avatar = None
        request.user.save()

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='User',
            target_id=request.user.id,
            description=f"Removed avatar for user '{request.user.username}'",
            hidden_description=f"User '{request.user.username}' removed their avatar",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    messages.success(request, "Avatar removed successfully.")
    return redirect('performanceevaluation:settings')


@login_required
@require_POST
def profile_update(request):
    user = request.user

    first_name = request.POST.get("first_name", "").strip()
    middle_name = request.POST.get("middle_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    username = request.POST.get("username", "").strip()
    phone = request.POST.get("phone", "").strip()
    bio = request.POST.get("bio", "").strip()

    if first_name:
        user.first_name = first_name
    if middle_name:
        user.middle_name = middle_name
    if last_name:
        user.last_name = last_name
    if username:
        user.username = username
    if phone:
        user.phone_number = phone
    if bio:
        user.bio = bio

    user.save()

    Logs.objects.create(
        user=user,
        system_name='performanceevaluation',
        action='UPDATE',
        target_model='User',
        target_id=user.id,
        description=f"Updated profile for user '{user.username}'",
        hidden_description=f"User '{user.username}' updated their profile",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    messages.success(request, "Profile updated successfully.")
    return redirect('performanceevaluation:settings')


@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password1 = request.POST.get("new_password1")
        new_password2 = request.POST.get("new_password2")
        user = request.user

        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('performanceevaluation:settings')

        if new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return redirect('performanceevaluation:settings')

        if len(new_password1) < 8:
            messages.error(request, "New password must be at least 8 characters long.")
            return redirect('performanceevaluation:settings')

        user.set_password(new_password1)
        user.save()
        update_session_auth_hash(request, user)

        Logs.objects.create(
            user=user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='User',
            target_id=user.id,
            description=f"Changed password for user '{user.username}'",
            hidden_description=f"User '{user.username}' changed their password",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, "Password changed successfully.")
        return redirect('performanceevaluation:settings')

    return redirect('performanceevaluation:settings')


@login_required
def save_addresses(request):
    if request.method != "POST":
        return redirect('performanceevaluation:settings')

    user = request.user

    home_address, created = Address.objects.get_or_create(
        user=user,
        type="home",
        defaults={
            "id": uuid.uuid4(),
            "full_address": encrypt(request.POST.get("address1", "")),
            "city": encrypt(request.POST.get("city1", "")),
            "province": encrypt(request.POST.get("province1", "")),
            "postal_code": encrypt(request.POST.get("zip1", "")),
            "country": encrypt(request.POST.get("country1", "")),
            "phone": encrypt(request.POST.get("phone1", "")),
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
        }
    )

    if created:
        Logs.objects.create(
            user=user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='Address',
            target_id=home_address.id,
            description=f"Created home address for user '{user.username}'",
            hidden_description=f"User '{user.username}' created their home address",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    else:
        home_address.full_address = encrypt(request.POST.get("address1", ""))
        home_address.city = encrypt(request.POST.get("city1", ""))
        home_address.province = encrypt(request.POST.get("province1", ""))
        home_address.postal_code = encrypt(request.POST.get("zip1", ""))
        home_address.country = encrypt(request.POST.get("country1", ""))
        home_address.phone = encrypt(request.POST.get("phone1", ""))
        home_address.updated_at = timezone.now()
        home_address.save()

        Logs.objects.create(
            user=user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='Address',
            target_id=home_address.id,
            description=f"Updated home address for user '{user.username}'",
            hidden_description=f"User '{user.username}' updated their home address",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    address2_value = request.POST.get("address2", "").strip()
    if address2_value:
        billing_address, created = Address.objects.get_or_create(
            user=user,
            type="billing",
            defaults={
                "id": uuid.uuid4(),
                "full_address": encrypt(address2_value),
                "city": encrypt(request.POST.get("city2", "")),
                "province": encrypt(request.POST.get("province2", "")),
                "postal_code": encrypt(request.POST.get("zip2", "")),
                "country": encrypt(request.POST.get("country2", "")),
                "phone": encrypt(request.POST.get("phone2", "")),
                "created_at": timezone.now(),
                "updated_at": timezone.now(),
            }
        )

        if created:
            Logs.objects.create(
                user=user,
                system_name='performanceevaluation',
                action='CREATE',
                target_model='Address',
                target_id=billing_address.id,
                description=f"Created billing address for user '{user.username}'",
                hidden_description=f"User '{user.username}' created their billing address",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
        else:
            billing_address.full_address = encrypt(address2_value)
            billing_address.city = encrypt(request.POST.get("city2", ""))
            billing_address.province = encrypt(request.POST.get("province2", ""))
            billing_address.postal_code = encrypt(request.POST.get("zip2", ""))
            billing_address.country = encrypt(request.POST.get("country2", ""))
            billing_address.phone = encrypt(request.POST.get("phone2", ""))
            billing_address.updated_at = timezone.now()
            billing_address.save()

            Logs.objects.create(
                user=user,
                system_name='performanceevaluation',
                action='UPDATE',
                target_model='Address',
                target_id=billing_address.id,
                description=f"Updated billing address for user '{user.username}'",
                hidden_description=f"User '{user.username}' updated their billing address",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )

    messages.success(request, "Addresses saved successfully.")
    return redirect('performanceevaluation:settings')


@login_required
@require_system_access
def delete_address(request, address_id):
    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
    )

    if address.type == 'home':
        messages.error(request, "Cannot delete home address.")
        return redirect('performanceevaluation:settings')

    if request.method == "POST":
        address.delete()

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='Address',
            target_id=address.id,
            description=f"Deleted address for user '{request.user.username}'",
            hidden_description=f"User '{request.user.username}' deleted an address",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, "Address deleted successfully.")

    return redirect('performanceevaluation:settings')

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def admin_dashboard(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()

    # Use the system key not display name
    memberships = SystemMembership.objects.filter(
        system_name='performanceevaluation'
    ).select_related('user').prefetch_related(
        'user__userdepartmentassignment_set__department'
    ).exclude(user_id=request.user.id).exclude(user__is_superuser=True)

    if search_query:
        memberships = memberships.filter(
            Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
        )

    total_users = memberships.count()
    total_admins = memberships.filter(system_role__in=['admin', 'superadmin']).count()
    total_evaluators = memberships.filter(system_role__in=['user', 'instructor']).count()

    paginator = Paginator(memberships, 10)
    page_number = request.GET.get('page') or 1
    memberships_page = paginator.get_page(page_number)

    # Get or create the system record
    system_record, created = Systems.objects.get_or_create(
        name='performanceevaluation',
        defaults={
            'description': 'Performance Evaluation System',
            'terms_of_service': 'Sample Terms of Service content for testing. Please update this with your actual terms.'
        }
    )
    tos_text = system_record.terms_of_service if system_record.terms_of_service else ''
    departments = Department.objects.filter(is_active=True).order_by('name')

    context = {
        'systems': systems,
        'current_system': current_system,
        'search_query': search_query,
        'memberships': memberships_page,
        'total_users': total_users,
        'total_admins': total_admins,
        'total_evaluators': total_evaluators,
        'tos_text': tos_text,
        'departments': departments,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'user_list_html': render_to_string(
                'performanceevaluation/partials/admin/_user_access_view.html',
                context,
                request=request,
            ),
            'total_users': total_users,
        })

    return render(request, 'performanceevaluation/pages/admin/dashboard.html', context)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def system_logs(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()

    logs_qs = Logs.objects.filter(system_name='performanceevaluation').order_by('-created_at')
    if search_query:
        logs_qs = logs_qs.filter(
            Q(user__username__icontains=search_query)
            | Q(action__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(target_model__icontains=search_query)
        )

    paginator = Paginator(logs_qs, 10)
    page_number = request.GET.get('page') or 1
    logs = paginator.get_page(page_number)

    context = {
        'systems': systems,
        'current_system': current_system,
        'search_query': search_query,
        'logs': logs,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logs_list_html = render_to_string(
            'performanceevaluation/partials/admin/_system_logs_table.html',
            context,
            request=request,
        )
        return JsonResponse({'logs_list_html': logs_list_html, 'search_query': search_query})

    return render(request, 'performanceevaluation/pages/admin/system_logs.html', context)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def manage_user_access(request, user_id):
    current_system = request.current_system
    membership = get_object_or_404(SystemMembership, user_id=user_id, system_name='performanceevaluation')
    new_role = request.POST.get('system_role', '').strip()
    department_id = request.POST.get('department', '').strip()

    if new_role not in ['user', 'instructor', 'admin', 'superadmin']:
        messages.error(request, 'Invalid role selected.')
        return redirect('performanceevaluation:admin_dashboard')

    membership.system_role = new_role
    membership.save(update_fields=['system_role'])

    # Handle department assignment
    if department_id:
        try:
            department = Department.objects.get(id=department_id)
            UserDepartmentAssignment.objects.update_or_create(
                user_id=user_id,
                defaults={'department': department}
            )
        except Department.DoesNotExist:
            messages.warning(request, 'Invalid department selected.')

    Logs.objects.create(
        user=request.user,
        system_name='performanceevaluation',
        action='UPDATE',
        target_model='SystemMembership',
        target_id=membership.id,
        description=f"Updated access for '{membership.user.username}' to '{new_role}'",
        hidden_description="",
    )

    messages.success(request, 'User access updated successfully.')
    return redirect('performanceevaluation:admin_dashboard')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def update_tos(request):
    current_system = request.current_system
    tos_content = request.POST.get('tos_text', '').strip()

    system = get_object_or_404(Systems, name='performanceevaluation')
    system.terms_of_service = tos_content
    system.save(update_fields=['terms_of_service'])

    Logs.objects.create(
        user=request.user,
        system_name='performanceevaluation',
        action='UPDATE',
        target_model='Systems',
        target_id=system.id,
        description='Updated Terms of Service content',
        hidden_description="",
    )

    messages.success(request, 'Terms of Service updated successfully.')
    return redirect('performanceevaluation:admin_dashboard')


# ===================== EVALUATION STRUCTURE =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def evaluation_structure(request):
    """Manage evaluation forms, categories, criteria, and rubrics"""
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])

    evaluation_cycles = EvaluationCycle.objects.select_related('term').order_by('-start_date')
    evaluation_forms_qs = EvaluationForm.objects.select_related('cycle', 'cycle__term').order_by('-id')
    evaluation_categories_qs = EvaluationCategory.objects.select_related('cycle', 'cycle__term').order_by('name')
    evaluation_criteria_qs = EvaluationCriterion.objects.select_related('category', 'category__cycle').order_by('name')
    rubrics_qs = Rubric.objects.select_related('criterion', 'criterion__category').order_by('criterion_id', 'level')

    forms_page = request.GET.get('forms_page') or 1
    categories_page = request.GET.get('categories_page') or 1
    criteria_page = request.GET.get('criteria_page') or 1
    rubrics_page = request.GET.get('rubrics_page') or 1

    evaluation_forms = Paginator(evaluation_forms_qs, 10).get_page(forms_page)
    evaluation_categories = Paginator(evaluation_categories_qs, 10).get_page(categories_page)
    evaluation_criteria = Paginator(evaluation_criteria_qs, 10).get_page(criteria_page)
    rubrics = Paginator(rubrics_qs, 10).get_page(rubrics_page)

    evaluator_types = EvaluationForm._meta.get_field('evaluator_type').choices

    context = {
        'systems': systems,
        'current_system': current_system,
        'evaluation_cycles': evaluation_cycles,
        'evaluation_forms': evaluation_forms,
        'evaluation_categories': evaluation_categories,
        'evaluation_criteria': evaluation_criteria,
        'rubrics': rubrics,
        'evaluator_types': evaluator_types,
    }

    return render(request, 'performanceevaluation/pages/admin/evaluation_structure.html', context)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_evaluation_form(request):
    cycle_id = request.POST.get('cycle', '').strip()
    evaluator_type = request.POST.get('evaluator_type', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    if not cycle_id or not evaluator_type:
        messages.error(request, 'Cycle and evaluator type are required.')
        return redirect('performanceevaluation:evaluation_structure')

    try:
        cycle = EvaluationCycle.objects.get(id=cycle_id)
        form = EvaluationForm.objects.create(
            cycle=cycle,
            evaluator_type=evaluator_type,
            is_active=is_active,
        )
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationForm',
            target_id=form.id,
            description=f"Created evaluation form: {evaluator_type}",
            hidden_description="",
        )
        messages.success(request, 'Evaluation form created successfully.')
    except EvaluationCycle.DoesNotExist:
        messages.error(request, 'Selected evaluation cycle does not exist.')
    except Exception as e:
        messages.error(request, f'Error creating evaluation form: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_evaluation_form(request, form_id):
    evaluation_form = get_object_or_404(EvaluationForm, id=form_id)
    cycle_id = request.POST.get('cycle', '').strip()
    evaluator_type = request.POST.get('evaluator_type', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    if not cycle_id or not evaluator_type:
        messages.error(request, 'Cycle and evaluator type are required.')
        return redirect('performanceevaluation:evaluation_structure')

    try:
        cycle = EvaluationCycle.objects.get(id=cycle_id)
        evaluation_form.cycle = cycle
        evaluation_form.evaluator_type = evaluator_type
        evaluation_form.is_active = is_active
        evaluation_form.save()
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='EvaluationForm',
            target_id=evaluation_form.id,
            description=f"Updated evaluation form: {evaluator_type}",
            hidden_description="",
        )
        messages.success(request, 'Evaluation form updated successfully.')
    except EvaluationCycle.DoesNotExist:
        messages.error(request, 'Selected evaluation cycle does not exist.')
    except Exception as e:
        messages.error(request, f'Error updating evaluation form: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_evaluation_form(request, form_id):
    evaluation_form = get_object_or_404(EvaluationForm, id=form_id)
    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='EvaluationForm',
            target_id=evaluation_form.id,
            description=f"Deleted evaluation form: {evaluation_form.evaluator_type}",
            hidden_description="",
        )
        evaluation_form.delete()
        messages.success(request, 'Evaluation form deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting evaluation form: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_evaluation_category(request):
    cycle_id = request.POST.get('cycle', '').strip()
    name = request.POST.get('name', '').strip()
    weight = request.POST.get('weight', '0').strip()

    if not cycle_id or not name:
        messages.error(request, 'Cycle and category name are required.')
        return redirect('performanceevaluation:evaluation_structure')

    try:
        cycle = EvaluationCycle.objects.get(id=cycle_id)
        category = EvaluationCategory.objects.create(
            cycle=cycle,
            name=name,
            weight=float(weight) if weight else 0.0,
        )
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationCategory',
            target_id=category.id,
            description=f"Created evaluation category: {name}",
            hidden_description="",
        )
        messages.success(request, 'Evaluation category created successfully.')
    except EvaluationCycle.DoesNotExist:
        messages.error(request, 'Selected evaluation cycle does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error creating evaluation category: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_evaluation_category(request, category_id):
    category = get_object_or_404(EvaluationCategory, id=category_id)
    cycle_id = request.POST.get('cycle', '').strip()
    name = request.POST.get('name', '').strip()
    weight = request.POST.get('weight', '0').strip()

    if not cycle_id or not name:
        messages.error(request, 'Cycle and category name are required.')
        return redirect('performanceevaluation:evaluation_structure')

    try:
        cycle = EvaluationCycle.objects.get(id=cycle_id)
        category.cycle = cycle
        category.name = name
        category.weight = float(weight) if weight else 0.0
        category.save()
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='EvaluationCategory',
            target_id=category.id,
            description=f"Updated evaluation category: {name}",
            hidden_description="",
        )
        messages.success(request, 'Evaluation category updated successfully.')
    except EvaluationCycle.DoesNotExist:
        messages.error(request, 'Selected evaluation cycle does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error updating evaluation category: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_evaluation_category(request, category_id):
    category = get_object_or_404(EvaluationCategory, id=category_id)
    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='EvaluationCategory',
            target_id=category.id,
            description=f"Deleted evaluation category: {category.name}",
            hidden_description="",
        )
        category.delete()
        messages.success(request, 'Evaluation category deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting evaluation category: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_evaluation_criteria(request):
    category_id = request.POST.get('category', '').strip()
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    weight = request.POST.get('weight', '0').strip()

    if not category_id or not name:
        messages.error(request, 'Category and criteria name are required.')
        return redirect('performanceevaluation:evaluation_structure')

    try:
        category = EvaluationCategory.objects.get(id=category_id)
        criteria = EvaluationCriterion.objects.create(
            category=category,
            name=name,
            description=description,
            weight=float(weight) if weight else 0.0,
        )
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationCriterion',
            target_id=criteria.id,
            description=f"Created evaluation criterion: {name}",
            hidden_description="",
        )
        messages.success(request, 'Evaluation criterion created successfully.')
    except EvaluationCategory.DoesNotExist:
        messages.error(request, 'Selected category does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error creating evaluation criterion: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_evaluation_criteria(request, criteria_id):
    criteria = get_object_or_404(EvaluationCriterion, id=criteria_id)
    category_id = request.POST.get('category', '').strip()
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    weight = request.POST.get('weight', '0').strip()

    if not category_id or not name:
        messages.error(request, 'Category and criteria name are required.')
        return redirect('performanceevaluation:evaluation_structure')

    try:
        category = EvaluationCategory.objects.get(id=category_id)
        criteria.category = category
        criteria.name = name
        criteria.description = description
        criteria.weight = float(weight) if weight else 0.0
        criteria.save()
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='EvaluationCriterion',
            target_id=criteria.id,
            description=f"Updated evaluation criterion: {name}",
            hidden_description="",
        )
        messages.success(request, 'Evaluation criterion updated successfully.')
    except EvaluationCategory.DoesNotExist:
        messages.error(request, 'Selected category does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error updating evaluation criterion: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_evaluation_criteria(request, criteria_id):
    criteria = get_object_or_404(EvaluationCriterion, id=criteria_id)
    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='EvaluationCriterion',
            target_id=criteria.id,
            description=f"Deleted evaluation criterion: {criteria.name}",
            hidden_description="",
        )
        criteria.delete()
        messages.success(request, 'Evaluation criterion deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting evaluation criterion: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_rubric(request):
    criterion_id = request.POST.get('criterion', '').strip()
    level = request.POST.get('level', '').strip()
    description = request.POST.get('description', '').strip()

    if not criterion_id or not level or not description:
        messages.error(request, 'Criterion, level, and description are required.')
        return redirect('performanceevaluation:evaluation_structure')

    try:
        criterion = EvaluationCriterion.objects.get(id=criterion_id)
        rubric = Rubric.objects.create(
            criterion=criterion,
            level=int(level),
            description=description,
        )
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='Rubric',
            target_id=rubric.id,
            description=f"Created rubric for {criterion.name} (Level {rubric.level})",
            hidden_description="",
        )
        messages.success(request, 'Rubric created successfully.')
    except EvaluationCriterion.DoesNotExist:
        messages.error(request, 'Selected criterion does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid level value: {str(e)}')
    except IntegrityError:
        messages.error(request, 'Rubric level already exists for this criterion.')
    except Exception as e:
        messages.error(request, f'Error creating rubric: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_rubric(request, rubric_id):
    rubric = get_object_or_404(Rubric, id=rubric_id)
    criterion_id = request.POST.get('criterion', '').strip()
    level = request.POST.get('level', '').strip()
    description = request.POST.get('description', '').strip()

    if not criterion_id or not level or not description:
        messages.error(request, 'Criterion, level, and description are required.')
        return redirect('performanceevaluation:evaluation_structure')

    try:
        criterion = EvaluationCriterion.objects.get(id=criterion_id)
        rubric.criterion = criterion
        rubric.level = int(level)
        rubric.description = description
        rubric.save()
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='Rubric',
            target_id=rubric.id,
            description=f"Updated rubric for {criterion.name} (Level {rubric.level})",
            hidden_description="",
        )
        messages.success(request, 'Rubric updated successfully.')
    except EvaluationCriterion.DoesNotExist:
        messages.error(request, 'Selected criterion does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid level value: {str(e)}')
    except IntegrityError:
        messages.error(request, 'Rubric level already exists for this criterion.')
    except Exception as e:
        messages.error(request, f'Error updating rubric: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_rubric(request, rubric_id):
    rubric = get_object_or_404(Rubric, id=rubric_id)
    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='Rubric',
            target_id=rubric.id,
            description=f"Deleted rubric: {rubric.criterion.name} (Level {rubric.level})",
            hidden_description="",
        )
        rubric.delete()
        messages.success(request, 'Rubric deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting rubric: {str(e)}')

    return redirect('performanceevaluation:evaluation_structure')


# ===================== EVALUATION ACTIVITY =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def evaluation_activity(request):
    """Manage evaluations, scores, and comments"""
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])

    evaluations_qs = Evaluation.objects.select_related(
        'form', 'form__cycle', 'form__cycle__term', 'evaluatee', 'evaluator'
    ).order_by('-id')
    scores_qs = EvaluationScore.objects.select_related(
        'evaluation', 'evaluation__evaluatee', 'criterion', 'criterion__category'
    ).order_by('-id')
    comments_qs = EvaluationComment.objects.select_related(
        'evaluation', 'evaluation__evaluatee'
    ).order_by('-id')

    evaluations_page = request.GET.get('evaluations_page') or 1
    scores_page = request.GET.get('scores_page') or 1
    comments_page = request.GET.get('comments_page') or 1

    evaluations = Paginator(evaluations_qs, 10).get_page(evaluations_page)
    evaluation_scores = Paginator(scores_qs, 10).get_page(scores_page)
    evaluation_comments = Paginator(comments_qs, 10).get_page(comments_page)

    evaluation_forms = EvaluationForm.objects.select_related('cycle', 'cycle__term').order_by('-id')
    criteria = EvaluationCriterion.objects.select_related('category').order_by('name')
    users = get_user_model().objects.all().order_by('username')
    evaluation_options = Evaluation.objects.select_related('form', 'evaluatee').order_by('-id')

    context = {
        'systems': systems,
        'current_system': current_system,
        'evaluations': evaluations,
        'evaluation_scores': evaluation_scores,
        'evaluation_comments': evaluation_comments,
        'evaluation_forms': evaluation_forms,
        'criteria': criteria,
        'users': users,
        'evaluation_options': evaluation_options,
    }

    return render(request, 'performanceevaluation/pages/admin/evaluation_activity.html', context)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_evaluation(request):
    form_id = request.POST.get('form', '').strip()
    evaluatee_id = request.POST.get('evaluatee', '').strip()
    evaluator_id = request.POST.get('evaluator', '').strip()
    submitted_at_raw = request.POST.get('submitted_at', '').strip()
    is_submitted = request.POST.get('is_submitted') == 'on'

    if not form_id or not evaluatee_id:
        messages.error(request, 'Form and evaluatee are required.')
        return redirect('performanceevaluation:evaluation_activity')

    try:
        form = EvaluationForm.objects.get(id=form_id)
        evaluatee = get_user_model().objects.get(id=evaluatee_id)
        evaluator = None
        if evaluator_id:
            evaluator = get_user_model().objects.get(id=evaluator_id)

        submitted_at = parse_datetime(submitted_at_raw) if submitted_at_raw else None
        if submitted_at and timezone.is_naive(submitted_at):
            submitted_at = timezone.make_aware(submitted_at)

        if is_submitted and not submitted_at:
            submitted_at = timezone.now()

        evaluation = Evaluation.objects.create(
            form=form,
            evaluatee=evaluatee,
            evaluator=evaluator,
            submitted_at=submitted_at,
            is_submitted=is_submitted,
        )
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='Evaluation',
            target_id=evaluation.id,
            description=f"Created evaluation for {evaluatee}",
            hidden_description="",
        )
        messages.success(request, 'Evaluation created successfully.')
    except EvaluationForm.DoesNotExist:
        messages.error(request, 'Selected evaluation form does not exist.')
    except get_user_model().DoesNotExist:
        messages.error(request, 'Selected user does not exist.')
    except Exception as e:
        messages.error(request, f'Error creating evaluation: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_evaluation(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    form_id = request.POST.get('form', '').strip()
    evaluatee_id = request.POST.get('evaluatee', '').strip()
    evaluator_id = request.POST.get('evaluator', '').strip()
    submitted_at_raw = request.POST.get('submitted_at', '').strip()
    is_submitted = request.POST.get('is_submitted') == 'on'

    if not form_id or not evaluatee_id:
        messages.error(request, 'Form and evaluatee are required.')
        return redirect('performanceevaluation:evaluation_activity')

    try:
        form = EvaluationForm.objects.get(id=form_id)
        evaluatee = get_user_model().objects.get(id=evaluatee_id)
        evaluator = None
        if evaluator_id:
            evaluator = get_user_model().objects.get(id=evaluator_id)

        submitted_at = parse_datetime(submitted_at_raw) if submitted_at_raw else None
        if submitted_at and timezone.is_naive(submitted_at):
            submitted_at = timezone.make_aware(submitted_at)

        if is_submitted and not submitted_at:
            submitted_at = timezone.now()

        evaluation.form = form
        evaluation.evaluatee = evaluatee
        evaluation.evaluator = evaluator
        evaluation.submitted_at = submitted_at
        evaluation.is_submitted = is_submitted
        evaluation.save()

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='Evaluation',
            target_id=evaluation.id,
            description=f"Updated evaluation for {evaluatee}",
            hidden_description="",
        )
        messages.success(request, 'Evaluation updated successfully.')
    except EvaluationForm.DoesNotExist:
        messages.error(request, 'Selected evaluation form does not exist.')
    except get_user_model().DoesNotExist:
        messages.error(request, 'Selected user does not exist.')
    except Exception as e:
        messages.error(request, f'Error updating evaluation: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_evaluation(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='Evaluation',
            target_id=evaluation.id,
            description=f"Deleted evaluation for {evaluation.evaluatee}",
            hidden_description="",
        )
        evaluation.delete()
        messages.success(request, 'Evaluation deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting evaluation: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_evaluation_score(request):
    evaluation_id = request.POST.get('evaluation', '').strip()
    criterion_id = request.POST.get('criterion', '').strip()
    score_value = request.POST.get('score', '').strip()

    if not evaluation_id or not criterion_id or score_value == '':
        messages.error(request, 'Evaluation, criterion, and score are required.')
        return redirect('performanceevaluation:evaluation_activity')

    try:
        evaluation = Evaluation.objects.get(id=evaluation_id)
        criterion = EvaluationCriterion.objects.get(id=criterion_id)
        score = EvaluationScore.objects.create(
            evaluation=evaluation,
            criterion=criterion,
            score=int(score_value),
        )
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationScore',
            target_id=score.id,
            description=f"Created score for {evaluation.evaluatee}",
            hidden_description="",
        )
        messages.success(request, 'Score created successfully.')
    except Evaluation.DoesNotExist:
        messages.error(request, 'Selected evaluation does not exist.')
    except EvaluationCriterion.DoesNotExist:
        messages.error(request, 'Selected criterion does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid score value: {str(e)}')
    except IntegrityError:
        messages.error(request, 'Score already exists for this evaluation and criterion.')
    except Exception as e:
        messages.error(request, f'Error creating score: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_evaluation_score(request, score_id):
    score = get_object_or_404(EvaluationScore, id=score_id)
    evaluation_id = request.POST.get('evaluation', '').strip()
    criterion_id = request.POST.get('criterion', '').strip()
    score_value = request.POST.get('score', '').strip()

    if not evaluation_id or not criterion_id or score_value == '':
        messages.error(request, 'Evaluation, criterion, and score are required.')
        return redirect('performanceevaluation:evaluation_activity')

    try:
        evaluation = Evaluation.objects.get(id=evaluation_id)
        criterion = EvaluationCriterion.objects.get(id=criterion_id)
        score.evaluation = evaluation
        score.criterion = criterion
        score.score = int(score_value)
        score.save()
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='EvaluationScore',
            target_id=score.id,
            description=f"Updated score for {evaluation.evaluatee}",
            hidden_description="",
        )
        messages.success(request, 'Score updated successfully.')
    except Evaluation.DoesNotExist:
        messages.error(request, 'Selected evaluation does not exist.')
    except EvaluationCriterion.DoesNotExist:
        messages.error(request, 'Selected criterion does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid score value: {str(e)}')
    except IntegrityError:
        messages.error(request, 'Score already exists for this evaluation and criterion.')
    except Exception as e:
        messages.error(request, f'Error updating score: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_evaluation_score(request, score_id):
    score = get_object_or_404(EvaluationScore, id=score_id)
    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='EvaluationScore',
            target_id=score.id,
            description=f"Deleted score for {score.evaluation.evaluatee}",
            hidden_description="",
        )
        score.delete()
        messages.success(request, 'Score deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting score: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_evaluation_comment(request):
    evaluation_id = request.POST.get('evaluation', '').strip()
    comment_text = request.POST.get('comment', '').strip()

    if not evaluation_id or not comment_text:
        messages.error(request, 'Evaluation and comment are required.')
        return redirect('performanceevaluation:evaluation_activity')

    try:
        evaluation = Evaluation.objects.get(id=evaluation_id)
        comment = EvaluationComment.objects.create(
            evaluation=evaluation,
            comment=comment_text,
        )
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationComment',
            target_id=comment.id,
            description=f"Created comment for {evaluation.evaluatee}",
            hidden_description="",
        )
        messages.success(request, 'Comment created successfully.')
    except Evaluation.DoesNotExist:
        messages.error(request, 'Selected evaluation does not exist.')
    except Exception as e:
        messages.error(request, f'Error creating comment: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_evaluation_comment(request, comment_id):
    comment = get_object_or_404(EvaluationComment, id=comment_id)
    evaluation_id = request.POST.get('evaluation', '').strip()
    comment_text = request.POST.get('comment', '').strip()

    if not evaluation_id or not comment_text:
        messages.error(request, 'Evaluation and comment are required.')
        return redirect('performanceevaluation:evaluation_activity')

    try:
        evaluation = Evaluation.objects.get(id=evaluation_id)
        comment.evaluation = evaluation
        comment.comment = comment_text
        comment.save()
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='EvaluationComment',
            target_id=comment.id,
            description=f"Updated comment for {evaluation.evaluatee}",
            hidden_description="",
        )
        messages.success(request, 'Comment updated successfully.')
    except Evaluation.DoesNotExist:
        messages.error(request, 'Selected evaluation does not exist.')
    except Exception as e:
        messages.error(request, f'Error updating comment: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_evaluation_comment(request, comment_id):
    comment = get_object_or_404(EvaluationComment, id=comment_id)
    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='EvaluationComment',
            target_id=comment.id,
            description=f"Deleted comment for {comment.evaluation.evaluatee}",
            hidden_description="",
        )
        comment.delete()
        messages.success(request, 'Comment deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting comment: {str(e)}')

    return redirect('performanceevaluation:evaluation_activity')


# ===================== RESULTS & ANALYTICS =====================

def _score_to_level(score_value):
    if score_value >= Decimal('4.50'):
        return 'Very High'
    if score_value >= Decimal('4.00'):
        return 'High'
    if score_value >= Decimal('3.00'):
        return 'Medium'
    if score_value >= Decimal('2.00'):
        return 'Low'
    return 'Very Low'


def _calculate_evaluation_score(evaluation):
    category_totals = {}
    category_weights = {}

    for score in evaluation.evaluationscore_set.all():
        criterion = score.criterion
        category = criterion.category

        totals = category_totals.setdefault(category.id, {'score_sum': 0.0, 'weight_sum': 0.0})
        weight = float(criterion.weight)
        totals['score_sum'] += float(score.score) * weight
        totals['weight_sum'] += weight
        category_weights[category.id] = float(category.weight)

    if not category_totals:
        return None

    weighted_sum = 0.0
    weight_total = 0.0

    for category_id, totals in category_totals.items():
        if totals['weight_sum'] <= 0:
            continue
        category_avg = totals['score_sum'] / totals['weight_sum']
        category_weight = category_weights.get(category_id, 1.0)
        weighted_sum += category_avg * category_weight
        weight_total += category_weight

    if weight_total <= 0:
        return None

    return weighted_sum / weight_total

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def results_analytics(request):
    """View computed results and recommendations"""
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])

    search_query = request.GET.get('search', '').strip()
    cycle_filter = request.GET.get('cycle', '').strip()
    level_filter = request.GET.get('performance_level', '').strip()
    sort_by = request.GET.get('sort', '').strip()
    sort_dir = request.GET.get('dir', '').strip().lower() or 'desc'

    sort_map = {
        'evaluatee': 'evaluatee__username',
        'cycle': 'cycle__term__name',
        'score': 'total_score',
        'level': 'performance_level',
        'computed': 'computed_at',
        'recommendations': 'recommendations_count',
    }

    results_qs = ComputedResult.objects.select_related('evaluatee', 'cycle', 'cycle__term')
    results_qs = results_qs.annotate(recommendations_count=Count('recommendation'))

    if search_query:
        results_qs = results_qs.filter(
            Q(evaluatee__username__icontains=search_query)
        )

    if cycle_filter:
        results_qs = results_qs.filter(cycle_id=cycle_filter)

    if level_filter:
        results_qs = results_qs.filter(performance_level__iexact=level_filter)

    sort_field = sort_map.get(sort_by)
    if sort_field:
        prefix = '-' if sort_dir == 'desc' else ''
        results_qs = results_qs.order_by(f'{prefix}{sort_field}', '-computed_at')
    else:
        results_qs = results_qs.order_by('-computed_at')

    page_number = request.GET.get('page') or 1
    results_page = Paginator(results_qs, 10).get_page(page_number)

    cycles = EvaluationCycle.objects.select_related('term').order_by('-start_date')

    context = {
        'systems': systems,
        'current_system': current_system,
        'search_query': search_query,
        'cycle_filter': cycle_filter,
        'level_filter': level_filter,
        'current_sort': sort_by,
        'current_dir': sort_dir,
        'results': results_page,
        'cycles': cycles,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        table_html = render_to_string(
            'performanceevaluation/partials/admin/_results_analytics_table.html',
            context,
            request=request,
        )
        return JsonResponse({'results_analytics_table_html': table_html})

    return render(request, 'performanceevaluation/pages/admin/results_analytics.html', context)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def compute_results(request):
    cycle_id = request.POST.get('cycle') or None

    evaluations_qs = Evaluation.objects.filter(is_submitted=True)
    if cycle_id:
        evaluations_qs = evaluations_qs.filter(form__cycle_id=cycle_id)

    evaluations_qs = evaluations_qs.select_related(
        'evaluatee',
        'form__cycle',
    ).prefetch_related(
        'evaluationscore_set__criterion__category'
    )

    results_bucket = {}
    for evaluation in evaluations_qs:
        computed = _calculate_evaluation_score(evaluation)
        if computed is None:
            continue
        key = (evaluation.evaluatee_id, evaluation.form.cycle_id)
        results_bucket.setdefault(key, []).append(computed)

    if not results_bucket:
        messages.warning(request, 'No evaluations available to compute.')
        return redirect('performanceevaluation:results_analytics')

    evaluatee_ids = [key[0] for key in results_bucket]
    cycle_ids = [key[1] for key in results_bucket]
    existing_results = ComputedResult.objects.filter(
        evaluatee_id__in=evaluatee_ids,
        cycle_id__in=cycle_ids,
    )
    existing_map = {(result.evaluatee_id, result.cycle_id): result for result in existing_results}

    created_count = 0
    updated_count = 0
    skipped_count = 0

    with transaction.atomic():
        for (evaluatee_id, cycle_key), scores in results_bucket.items():
            avg_score = sum(scores) / len(scores)
            score_decimal = Decimal(str(avg_score)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            performance_level = _score_to_level(score_decimal)

            existing = existing_map.get((evaluatee_id, cycle_key))
            if existing and existing.is_locked:
                skipped_count += 1
                continue

            if existing:
                existing.total_score = score_decimal
                existing.performance_level = performance_level
                existing.save(update_fields=['total_score', 'performance_level'])
                updated_count += 1
            else:
                ComputedResult.objects.create(
                    evaluatee_id=evaluatee_id,
                    cycle_id=cycle_key,
                    total_score=score_decimal,
                    performance_level=performance_level,
                )
                created_count += 1

    message_parts = []
    if created_count:
        message_parts.append(f'{created_count} created')
    if updated_count:
        message_parts.append(f'{updated_count} updated')
    if skipped_count:
        message_parts.append(f'{skipped_count} locked')
    message = ', '.join(message_parts) if message_parts else 'No results computed.'
    messages.success(request, f'Computed results: {message}.')

    return redirect('performanceevaluation:results_analytics')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def results_analytics_recommendations(request, result_id):
    result = get_object_or_404(ComputedResult, id=result_id)
    recommendations = Recommendation.objects.filter(result=result).order_by('-created_at')

    html = render_to_string(
        'performanceevaluation/partials/admin/_results_analytics_recommendations_table.html',
        {
            'result': result,
            'recommendations': recommendations,
        },
        request=request,
    )
    return JsonResponse({'recommendations_html': html})


# ===================== CRITERIA & RUBRICS MANAGEMENT =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def criteria_rubrics(request):
    """View evaluation criteria and rubrics"""
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()

    criteria_qs = EvaluationCriterion.objects.select_related('category')
    
    if search_query:
        criteria_qs = criteria_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        criteria_qs = criteria_qs.filter(category_id=category_filter)

    # Get all categories and academic terms
    categories = EvaluationCategory.objects.all()
    academic_terms = AcademicTerm.objects.all().order_by('-start_date')

    paginator = Paginator(criteria_qs, 10)
    page_number = request.GET.get('page') or 1
    criteria_list = paginator.get_page(page_number)

    context = {
        'systems': systems,
        'current_system': current_system,
        'search_query': search_query,
        'criteria_list': criteria_list,
        'categories': categories,
        'academic_terms': academic_terms,
        'category_filter': category_filter,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        criteria_html = render_to_string(
            'performanceevaluation/partials/admin/_criteria_list.html',
            context,
            request=request,
        )
        return JsonResponse({'criteria_html': criteria_html})

    return render(request, 'performanceevaluation/pages/admin/criteria_rubrics.html', context)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_criteria(request):
    """Add a new evaluation criterion"""
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    category_id = request.POST.get('category', '').strip()
    weight = request.POST.get('weight', '0').strip()

    if not name:
        messages.error(request, 'Criterion name is required.')
        return redirect('performanceevaluation:criteria_rubrics')
    
    if not category_id:
        messages.error(request, 'Category is required.')
        return redirect('performanceevaluation:criteria_rubrics')

    try:
        category = EvaluationCategory.objects.get(id=category_id)
        criteria = EvaluationCriterion.objects.create(
            name=name,
            description=description,
            category=category,
            weight=float(weight) if weight else 0.0
        )

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationCriterion',
            target_id=criteria.id,
            description=f"Created evaluation criterion: {name}",
            hidden_description="",
        )

        messages.success(request, f'Criterion "{name}" created successfully.')
    except EvaluationCategory.DoesNotExist:
        messages.error(request, 'Selected category does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    
    return redirect('performanceevaluation:criteria_rubrics')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_criteria(request, criteria_id):
    """Edit an evaluation criterion"""
    criteria = get_object_or_404(EvaluationCriterion, id=criteria_id)
    
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    category_id = request.POST.get('category', '').strip()
    weight = request.POST.get('weight', '0').strip()

    if not name:
        messages.error(request, 'Criterion name is required.')
        return redirect('performanceevaluation:criteria_rubrics')

    try:
        if category_id:
            category = EvaluationCategory.objects.get(id=category_id)
            criteria.category = category
        
        criteria.name = name
        criteria.description = description
        criteria.weight = float(weight) if weight else 0.0
        criteria.save()

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='EvaluationCriterion',
            target_id=criteria.id,
            description=f"Updated evaluation criterion: {name}",
            hidden_description="",
        )

        messages.success(request, f'Criterion "{name}" updated successfully.')
    except EvaluationCategory.DoesNotExist:
        messages.error(request, 'Selected category does not exist.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    
    return redirect('performanceevaluation:criteria_rubrics')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_criteria(request, criteria_id):
    """Delete an evaluation criterion"""
    criteria = get_object_or_404(EvaluationCriterion, id=criteria_id)
    criteria_name = criteria.name

    Logs.objects.create(
        user=request.user,
        system_name='performanceevaluation',
        action='DELETE',
        target_model='EvaluationCriterion',
        target_id=criteria.id,
        description=f"Deleted evaluation criterion: {criteria_name}",
        hidden_description="",
    )

    criteria.delete()
    messages.success(request, f'Criterion "{criteria_name}" deleted successfully.')
    return redirect('performanceevaluation:criteria_rubrics')


# ===================== ACADEMIC TERM MANAGEMENT =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_academic_term(request):
    """Add a new academic term"""
    name = request.POST.get('name', '').strip()
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    if not name:
        messages.error(request, 'Term name is required.')
        return redirect('performanceevaluation:criteria_rubrics')
    
    if not start_date or not end_date:
        messages.error(request, 'Start date and end date are required.')
        return redirect('performanceevaluation:criteria_rubrics')

    try:
        academic_term = AcademicTerm.objects.create(
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active
        )

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='AcademicTerm',
            target_id=academic_term.id,
            description=f"Created academic term: {name}",
            hidden_description="",
        )

        messages.success(request, f'Academic term "{name}" created successfully.')
    except Exception as e:
        messages.error(request, f'Error creating academic term: {str(e)}')
    
    return redirect('performanceevaluation:criteria_rubrics')


# ===================== EVALUATION CATEGORY MANAGEMENT =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def add_eval_category(request):
    """Add a new evaluation category"""
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    weight = request.POST.get('weight', '1.0').strip()

    if not name:
        messages.error(request, 'Category name is required.')
        return redirect('performanceevaluation:criteria_rubrics')

    try:
        category = EvaluationCategory.objects.create(
            name=name,
            description=description,
            weight=float(weight) if weight else 1.0
        )

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationCategory',
            target_id=category.id,
            description=f"Created evaluation category: {name}",
            hidden_description="",
        )

        messages.success(request, f'Category "{name}" created successfully.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error creating category: {str(e)}')
    
    return redirect('performanceevaluation:criteria_rubrics')


# ===================== ACADEMIC SETUP PAGE =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def academic_setup(request):
    """View academic setup page with terms, cycles, and departments"""
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])

    academic_terms_qs = AcademicTerm.objects.all().order_by('-start_date')
    evaluation_cycles_qs = EvaluationCycle.objects.select_related('term').all().order_by('-start_date')
    departments_qs = Department.objects.all().order_by('name')

    terms_page = request.GET.get('terms_page') or 1
    cycles_page = request.GET.get('cycles_page') or 1
    departments_page = request.GET.get('departments_page') or 1

    academic_terms = Paginator(academic_terms_qs, 10).get_page(terms_page)
    evaluation_cycles = Paginator(evaluation_cycles_qs, 10).get_page(cycles_page)
    departments = Paginator(departments_qs, 10).get_page(departments_page)
    
    context = {
        'systems': systems,
        'current_system': current_system,
        'academic_terms': academic_terms,
        'evaluation_cycles': evaluation_cycles,
        'departments': departments,
    }
    
    return render(request, 'performanceevaluation/pages/admin/academic_setup.html', context)


# ===================== ACADEMIC TERM MANAGEMENT =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_academic_term(request):
    """Add a new academic term"""
    name = request.POST.get('name', '').strip()
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    if not name:
        messages.error(request, 'Term name is required.')
        return redirect('performanceevaluation:academic_setup')
    
    if not start_date or not end_date:
        messages.error(request, 'Start date and end date are required.')
        return redirect('performanceevaluation:academic_setup')

    try:
        academic_term = AcademicTerm.objects.create(
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active
        )

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='AcademicTerm',
            target_id=academic_term.id,
            description=f"Created academic term: {name}",
            hidden_description="",
        )

        messages.success(request, f'Academic term "{name}" created successfully.')
    except Exception as e:
        messages.error(request, f'Error creating academic term: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_academic_term(request, term_id):
    """Edit an existing academic term"""
    academic_term = get_object_or_404(AcademicTerm, id=term_id)
    
    name = request.POST.get('name', '').strip()
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    if not name:
        messages.error(request, 'Term name is required.')
        return redirect('performanceevaluation:academic_setup')
    
    if not start_date or not end_date:
        messages.error(request, 'Start date and end date are required.')
        return redirect('performanceevaluation:academic_setup')

    try:
        academic_term.name = name
        academic_term.start_date = start_date
        academic_term.end_date = end_date
        academic_term.is_active = is_active
        academic_term.save()

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='AcademicTerm',
            target_id=academic_term.id,
            description=f"Updated academic term: {name}",
            hidden_description="",
        )

        messages.success(request, f'Academic term "{name}" updated successfully.')
    except Exception as e:
        messages.error(request, f'Error updating academic term: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_academic_term(request, term_id):
    """Delete an academic term"""
    academic_term = get_object_or_404(AcademicTerm, id=term_id)
    term_name = academic_term.name

    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='AcademicTerm',
            target_id=academic_term.id,
            description=f"Deleted academic term: {term_name}",
            hidden_description="",
        )

        academic_term.delete()
        messages.success(request, f'Academic term "{term_name}" deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting academic term: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')


# ===================== EVALUATION CYCLE MANAGEMENT =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_evaluation_cycle(request):
    """Add a new evaluation cycle"""
    name = request.POST.get('name', '').strip()
    term_id = request.POST.get('term', '').strip()
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip()

    if not name:
        messages.error(request, 'Cycle name is required.')
        return redirect('performanceevaluation:academic_setup')
    
    if not term_id:
        messages.error(request, 'Academic term is required.')
        return redirect('performanceevaluation:academic_setup')
    
    if not start_date or not end_date:
        messages.error(request, 'Start date and end date are required.')
        return redirect('performanceevaluation:academic_setup')

    try:
        term = AcademicTerm.objects.get(id=term_id)
        evaluation_cycle = EvaluationCycle.objects.create(
            name=name,
            term=term,
            start_date=start_date,
            end_date=end_date,
            is_closed=False
        )

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationCycle',
            target_id=evaluation_cycle.id,
            description=f"Created evaluation cycle: {name}",
            hidden_description="",
        )

        messages.success(request, f'Evaluation cycle "{name}" created successfully.')
    except AcademicTerm.DoesNotExist:
        messages.error(request, 'Selected academic term does not exist.')
    except Exception as e:
        messages.error(request, f'Error creating evaluation cycle: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_evaluation_cycle(request, cycle_id):
    """Edit an existing evaluation cycle"""
    evaluation_cycle = get_object_or_404(EvaluationCycle, id=cycle_id)
    
    name = request.POST.get('name', '').strip()
    term_id = request.POST.get('term', '').strip()
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip()
    is_closed = request.POST.get('is_closed') == 'on'

    if not name:
        messages.error(request, 'Cycle name is required.')
        return redirect('performanceevaluation:academic_setup')
    
    if not term_id:
        messages.error(request, 'Academic term is required.')
        return redirect('performanceevaluation:academic_setup')
    
    if not start_date or not end_date:
        messages.error(request, 'Start date and end date are required.')
        return redirect('performanceevaluation:academic_setup')

    try:
        term = AcademicTerm.objects.get(id=term_id)
        evaluation_cycle.name = name
        evaluation_cycle.term = term
        evaluation_cycle.start_date = start_date
        evaluation_cycle.end_date = end_date
        evaluation_cycle.is_closed = is_closed
        evaluation_cycle.save()

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='EvaluationCycle',
            target_id=evaluation_cycle.id,
            description=f"Updated evaluation cycle: {name}",
            hidden_description="",
        )

        messages.success(request, f'Evaluation cycle "{name}" updated successfully.')
    except AcademicTerm.DoesNotExist:
        messages.error(request, 'Selected academic term does not exist.')
    except Exception as e:
        messages.error(request, f'Error updating evaluation cycle: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_evaluation_cycle(request, cycle_id):
    """Delete an evaluation cycle"""
    evaluation_cycle = get_object_or_404(EvaluationCycle, id=cycle_id)
    cycle_name = evaluation_cycle.name

    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='EvaluationCycle',
            target_id=evaluation_cycle.id,
            description=f"Deleted evaluation cycle: {cycle_name}",
            hidden_description="",
        )

        evaluation_cycle.delete()
        messages.success(request, f'Evaluation cycle "{cycle_name}" deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting evaluation cycle: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')


# ===================== DEPARTMENT MANAGEMENT =====================

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def add_department(request):
    """Add a new department"""
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    if not name:
        messages.error(request, 'Department name is required.')
        return redirect('performanceevaluation:academic_setup')
    
    if not code:
        messages.error(request, 'Department code is required.')
        return redirect('performanceevaluation:academic_setup')

    try:
        # Check if code already exists
        if Department.objects.filter(code=code).exists():
            messages.error(request, f'Department code "{code}" already exists.')
            return redirect('performanceevaluation:academic_setup')
        
        department = Department.objects.create(
            name=name,
            code=code,
            is_active=is_active
        )

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='Department',
            target_id=department.id,
            description=f"Created department: {name} ({code})",
            hidden_description="",
        )

        messages.success(request, f'Department "{name}" created successfully.')
    except Exception as e:
        messages.error(request, f'Error creating department: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def edit_department(request, dept_id):
    """Edit an existing department"""
    department = get_object_or_404(Department, id=dept_id)
    
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    if not name:
        messages.error(request, 'Department name is required.')
        return redirect('performanceevaluation:academic_setup')
    
    if not code:
        messages.error(request, 'Department code is required.')
        return redirect('performanceevaluation:academic_setup')

    try:
        # Check if code already exists (excluding current department)
        if Department.objects.filter(code=code).exclude(id=dept_id).exists():
            messages.error(request, f'Department code "{code}" already exists.')
            return redirect('performanceevaluation:academic_setup')
        
        department.name = name
        department.code = code
        department.is_active = is_active
        department.save()

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='UPDATE',
            target_model='Department',
            target_id=department.id,
            description=f"Updated department: {name} ({code})",
            hidden_description="",
        )

        messages.success(request, f'Department "{name}" updated successfully.')
    except Exception as e:
        messages.error(request, f'Error updating department: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def delete_department(request, dept_id):
    """Delete a department"""
    department = get_object_or_404(Department, id=dept_id)
    dept_name = department.name

    try:
        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='DELETE',
            target_model='Department',
            target_id=department.id,
            description=f"Deleted department: {dept_name}",
            hidden_description="",
        )

        department.delete()
        messages.success(request, f'Department "{dept_name}" deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting department: {str(e)}')
    
    return redirect('performanceevaluation:academic_setup')
    """Add a new evaluation category"""
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    weight = request.POST.get('weight', '1.0').strip()

    if not name:
        messages.error(request, 'Category name is required.')
        return redirect('performanceevaluation:criteria_rubrics')

    try:
        category = EvaluationCategory.objects.create(
            name=name,
            description=description,
            weight=float(weight) if weight else 1.0
        )

        Logs.objects.create(
            user=request.user,
            system_name='performanceevaluation',
            action='CREATE',
            target_model='EvaluationCategory',
            target_id=category.id,
            description=f"Created evaluation category: {name}",
            hidden_description="",
        )

        messages.success(request, f'Category "{name}" created successfully.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error creating category: {str(e)}')
    
    return redirect('performanceevaluation:criteria_rubrics')