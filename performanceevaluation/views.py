from django.http import Http404, JsonResponse, HttpResponse
from django.views.defaults import page_not_found
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField
from .models import Performance
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