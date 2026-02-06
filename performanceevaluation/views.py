from django.http import Http404, JsonResponse, HttpResponse
from django.views.defaults import page_not_found
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField
from .models import (
    EvaluationCriterion, EvaluationCategory, 
    AcademicTerm, EvaluationCycle, Rubric, Department
)
from core.decorators import require_system_access, require_system_role
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from core.models import Logs, SystemMembership, Systems
from django.core.paginator import Paginator
import json
from datetime import datetime, timedelta


@login_required
@require_system_access
@require_system_role(['user', 'superadmin'])
def dashboard(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    
    # Get basic statistics (these would come from actual models in production)
    total_teachers = 247
    pending_evaluations = 34
    avg_score = 4.2
    high_performers = 89
    
    # Sample data for recent evaluations
    recent_evaluations = [
        {
            'teacher_name': 'Dr. Sarah Mitchell',
            'performance_level': 'High',
            'subject': 'Mathematics',
            'score': '4.8/5.0'
        },
        {
            'teacher_name': 'Prof. James Chen',
            'performance_level': 'High',
            'subject': 'Science',
            'score': '4.6/5.0'
        },
        {
            'teacher_name': 'Ms. Emily Rodriguez',
            'performance_level': 'Average',
            'subject': 'English',
            'score': '4.2/5.0'
        },
        {
            'teacher_name': 'Mr. David Thompson',
            'performance_level': 'Average',
            'subject': 'History',
            'score': '4/5.0'
        },
        {
            'teacher_name': 'Ms. Rachel Green',
            'performance_level': 'Needs Improvement',
            'subject': 'Arts',
            'score': '3.5/5.0'
        }
    ]
    
    # Sample data for notifications
    recent_notifications = [
        {
            'message': 'New evaluation submitted by Dr. Sarah Mitchell',
            'time_ago': '2 hours ago'
        },
        {
            'message': 'Evaluation cycle deadline approaching (5 days)',
            'time_ago': '5 hours ago'
        },
        {
            'message': 'Department report generated for Mathematics',
            'time_ago': '1 day ago'
        },
        {
            'message': 'Performance review meeting scheduled',
            'time_ago': '2 days ago'
        }
    ]
    
    context = {
        'systems': systems,
        'current_system': current_system,
        'total_teachers': total_teachers,
        'pending_evaluations': pending_evaluations,
        'avg_score': avg_score,
        'high_performers': high_performers,
        'recent_evaluations': recent_evaluations,
        'recent_notifications': recent_notifications,
    }
    
    return render(request, 'performanceevaluation/pages/dashboard.html', context)

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
    ).select_related('user').exclude(user_id=request.user.id).exclude(user__is_superuser=True)

    if search_query:
        memberships = memberships.filter(
            Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
        )

    total_users = memberships.count()
    total_admins = memberships.filter(system_role__in=['admin', 'superadmin']).count()
    total_evaluators = memberships.filter(system_role='user').count()

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

    context = {
        'systems': systems,
        'current_system': current_system,
        'search_query': search_query,
        'memberships': memberships_page,
        'total_users': total_users,
        'total_admins': total_admins,
        'total_evaluators': total_evaluators,
        'tos_text': tos_text,
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

    if new_role not in ['user', 'admin', 'superadmin']:
        messages.error(request, 'Invalid role selected.')
        return redirect('performanceevaluation:admin_dashboard')

    membership.system_role = new_role
    membership.save(update_fields=['system_role'])

    Logs.objects.create(
        user=request.user,
        system_name='performanceevaluation',
        action='UPDATE',
        target_model='SystemMembership',
        target_id=membership.id,
        description=f"Updated access for '{membership.user.username}' to '{new_role}'",
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
    )

    messages.success(request, 'Terms of Service updated successfully.')
    return redirect('performanceevaluation:admin_dashboard')


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
    
    academic_terms = AcademicTerm.objects.all().order_by('-start_date')
    evaluation_cycles = EvaluationCycle.objects.select_related('term').all().order_by('-start_date')
    departments = Department.objects.all().order_by('name')
    
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
        )

        messages.success(request, f'Category "{name}" created successfully.')
    except (ValueError, TypeError) as e:
        messages.error(request, f'Invalid weight value: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error creating category: {str(e)}')
    
    return redirect('performanceevaluation:criteria_rubrics')