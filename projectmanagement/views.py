from django.shortcuts import render, redirect,  get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from .models import Project, Task, Team
from core.models import Logs, SystemMembership, Systems, Address
from core.utils import get_client_ip, get_user_agent, decrypt, encrypt
import uuid
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
import json

now = timezone.now()
User = get_user_model()


def dashboard(request):
    current_system = request.current_system

    # ---- Access control ----
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).exists():
        return render(request, '404.html', status=404)

    # ---- Get current user's role ----
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']

    # ---- Get search query ----
    search_query = request.GET.get('search', '').strip()

    # ---- Base querysets ----
    projects = Project.objects.prefetch_related("tasks")
    all_tasks = (
        Task.objects
        .select_related("project")
        .prefetch_related("assigned_to", "assigned_team__members")
    )
    
    # ---- Create separate querysets for stats (show all for admin/superuser) ----
    if is_admin_or_superadmin:
        # Admins and superusers see all projects and tasks in stats
        stats_projects = Project.objects.prefetch_related("tasks")
        stats_tasks = (
            Task.objects
            .select_related("project")
            .prefetch_related("assigned_to", "assigned_team__members")
        )
    else:
        # Regular users only see their assigned tasks in stats
        stats_projects = projects.filter(tasks__assigned_to=request.user).distinct()
        stats_tasks = all_tasks.filter(assigned_to=request.user)
    
    # ---- Apply visibility scope based on user role ----
    if not is_admin_or_superadmin:
        # Regular users only see tasks assigned to them
        all_tasks = all_tasks.filter(assigned_to=request.user)
        projects = projects.filter(tasks__assigned_to=request.user).distinct()
    # Admins and superusers can see all projects and tasks (no filtering)

    # ---- Apply search filter ----
    if search_query:
        all_tasks = all_tasks.filter(
            Q(title__icontains=search_query) |
            Q(project__name__icontains=search_query)
        )
        
        projects = projects.filter(
            Q(name__icontains=search_query) |
            Q(tasks__title__icontains=search_query)
        ).distinct()

    # ---- Time-aware project states (using stats querysets for admin/superuser) ----
    active_projects = stats_projects.filter(
        start_date__lte=now,
        end_date__gte=now
    )

    past_projects = stats_projects.filter(
        end_date__lt=now
    )

    active_projects_count = active_projects.count()

    # ---- Time-aware task states (using stats querysets for admin/superuser) ----
    active_tasks = stats_tasks.exclude(
        status='completed'
    ).filter(
        due_date__gte=now
    )

    overdue_tasks = stats_tasks.exclude(
        status='completed'
    ).filter(
        due_date__lt=now
    )

    active_tasks_count = active_tasks.count()

    # ---- Total stats (for all projects/tasks visible to user) ----
    total_projects_count = stats_projects.count()
    total_tasks_count = stats_tasks.exclude(status='completed').count()

    # ---- Assignment stats (for paginated display) ----
    assigned_projects_count = projects.count()
    assigned_tasks_count = all_tasks.count()

    # ---- Late/Overdue stats ----
    late_projects_count = past_projects.count()
    late_tasks_count = overdue_tasks.count()

    # ---- Kanban buckets ----
    # Normalize status to lowercase for consistent matching
    todo_tasks = all_tasks.filter(status='todo')
    in_progress_tasks = all_tasks.filter(status='in_progress')
    completed_tasks = all_tasks.filter(status='completed')

    # ---- Pagination ----
    paginator_projects = Paginator(projects, 5)  # 5 projects per page
    page_number = request.GET.get('page', 1)
    projects_page = paginator_projects.get_page(page_number)

    context = {
        'projects': projects_page,
        'projects_paginator': paginator_projects,
        'projects_page_number': page_number,
        'current_system': current_system,
        'now': now,
        # Stats - Total counts
        'total_projects_count': total_projects_count,
        'total_tasks_count': total_tasks_count,
        # Stats - Active/Late counts
        'active_projects_count': active_projects_count,
        'active_tasks_count': active_tasks_count,
        'late_projects_count': late_projects_count,
        'late_tasks_count': late_tasks_count,
        # Assignment counts (for display)
        'assigned_projects_count': assigned_projects_count,
        'assigned_tasks_count': assigned_tasks_count,
        # Kanban
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        # Optional future use
        'overdue_task_ids': set(overdue_tasks.values_list('id', flat=True)),
        'past_projects': past_projects,
        'search_query': search_query,
    }

    # ---- Handle AJAX requests ----
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        kanban_html = render_to_string(
            'projectmanagement/partials/_kanban_view.html',
            context,
            request=request
        )
        table_html = render_to_string(
            'projectmanagement/partials/_table_view.html',
            context,
            request=request
        )
        stats_html = render_to_string(
            'projectmanagement/partials/_stats.html',
            context,
            request=request
        )
        
        return JsonResponse({
            'kanban_html': kanban_html,
            'table_html': table_html,
            'stats_html': stats_html,
            'search_query': search_query,
        })

    # ---- Regular page load ----
    return render(
        request,
        'projectmanagement/pages/dashboard.html',
        context
    )

def admin_dashboard(request):
    current_system = request.current_system  # set by middleware

    ROLE_LABELS = {
        'superadmin': 'Super Admin',
        'admin': 'Admin',
        'user': 'User',
        # add other roles as needed
    }

    # Fetch the Terms of Service for the current system
    tos_text = Systems.objects.filter(name=current_system).values_list('terms_of_service', flat=True).first() or ''

    # ---- Get search query ----
    search_query = request.GET.get('search', '').strip()

    # Get users based on superuser or normal admin role
    if request.user.is_superuser:
        users_qs = (
            User.objects
            .filter(systemmembership__system_name=current_system)
            .exclude(is_superuser=True)
            .exclude(id=request.user.id)
            .distinct()
            .order_by('-date_joined')
        )
    else:
        users_qs = (
            User.objects
            .filter(systemmembership__system_name=current_system)
            .exclude(is_superuser=True)
            .exclude(id=request.user.id)
            .exclude(systemmembership__system_role='superadmin')
            .distinct()
            .order_by('-date_joined')
        )

    # ---- Apply search filter ----
    if search_query:
        q_lower = search_query.lower()
        matched_ids = []

        # Names are decrypted via model properties; email is plaintext.
        for u in users_qs:
            fields = [
                str(getattr(u, 'username', '') or ''),
                (getattr(u, 'first_name', '') or ''),
                (getattr(u, 'last_name', '') or ''),
                str(getattr(u, 'email', '') or ''),
            ]

            if any(q_lower in (f or '').lower() for f in fields):
                matched_ids.append(u.id)

        users_qs = users_qs.filter(id__in=matched_ids)

    # Fetch roles for users in this system
    system_roles = {
        m.user_id: (m.system_role, ROLE_LABELS.get(m.system_role, m.system_role.title()))
        for m in SystemMembership.objects.filter(
            system_name=current_system,
            user__in=users_qs
        )
    }

    paginator = Paginator(users_qs, 2)
    # Honor requested page even when searching
    page_number = request.GET.get('page') or 1
    users = paginator.get_page(page_number)

    current_user_role = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).values_list('system_role', flat=True).first()

    context = {
        'users': users,
        'total_users': users_qs.count(),
        'current_system': current_system,
        'system_roles': system_roles,
        'current_user_role': current_user_role,
        'tos_text': tos_text,
        'search_query': search_query,
    }

    # ---- Handle AJAX requests ----
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        user_list_html = render_to_string(
            'projectmanagement/partials/admin/_user_access_view.html',
            context,
            request=request
        )
        
        return JsonResponse({
            'user_list_html': user_list_html,
            'total_users': users_qs.count(),
            'search_query': search_query,
        })

    # ---- Regular page load ----
    return render(
        request,
        'projectmanagement/pages/admin/dashboard.html',
        context
    )


def settings(request):
    current_system = request.current_system  # set by middleware

    # Superuser bypass
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user, system_name=current_system
    ).exists():
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])

    home_address = request.user.addresses.filter(type='home').first()
    secondary_address = request.user.addresses.filter(type='billing').first()

    current_user_role = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).values_list('system_role', flat=True).first()

    # Decrypt addresses if they exist
    for addr in (home_address, secondary_address):
        if addr:
            addr.full_address = decrypt(addr.full_address)
            addr.city = decrypt(addr.city)
            addr.province = decrypt(addr.province)
            addr.postal_code = decrypt(addr.postal_code)
            addr.country = decrypt(addr.country)
            if getattr(addr, 'phone', None):
                addr.phone = decrypt(addr.phone)

    return render(
        request,
        'projectmanagement/pages/settings.html',
        {
            'systems': systems,
            'home_address': home_address,
            'secondary_address': secondary_address,
            'current_system': current_system,
            'current_user_role': current_user_role,
        }
    )


@require_http_methods(["POST"])
def deactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    
    Logs.objects.create(
        user=request.user,
        system_name='projectmanagement',
        action='UPDATE',
        target_model='User',
        target_id=user.id,  # Fixed: was target_user.id
        description=f"Deactivated user '{user.username}'",
        hidden_description=f"Deactivated user '{user.username}'"
    )

    return redirect("projectmanagement:pm_admin_dashboard") 


@require_http_methods(["POST"])
def activate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    
    Logs.objects.create(
        user=request.user,
        system_name='projectmanagement',
        action='UPDATE',
        target_model='User',
        target_id=user.id,  # Fixed: was target_user.id
        description=f"Activated user '{user.username}'",
        hidden_description=f"Activated user '{user.username}'"
    )
    
    return redirect("projectmanagement:pm_admin_dashboard") 

def delete_user(request, user_id):
    """
    Delete a user by their ID.
    Only accessible by system_role = superusers.
    """
    current_system = request.current_system  # set by middleware

    current_user_role = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).values_list('system_role', flat=True).first()


    if not request.user.is_superuser and current_user_role != 'superadmin':
        messages.error(request, "You do not have permission to perform this action.")
        return redirect("projectmanagement:pm_admin_dashboard") 

    target_user = get_object_or_404(User, id=user_id)

    if request.user == target_user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("projectmanagement:pm_admin_dashboard") 

    if request.method == 'POST':
        username = target_user.username
        target_user.delete()

        Logs.objects.create(
            user=request.user,
            system_name='projectmanagement',
            action='DELETE',
            target_model='User',
            target_id=user_id,
            description=f"Deleted user '{request.user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        Logs.objects.create(
            user=request.user,
            system_name='projectmanagement',
            action='DELETE',
            target_model='SystemMembership',
            target_id=None,
            description=f"Deleted all system memberships for user '{username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, f"User '{username}' has been deleted.")
        return redirect("projectmanagement:pm_admin_dashboard") 

    # If not POST, redirect to dashboard
    return redirect("projectmanagement:pm_admin_dashboard") 

def manage_user_access(request, user_id):
    """
    Manage user access levels within the current system.
    """
    if request.method == 'POST':
        new_role = request.POST.get('access_level')
        current_system = request.current_system  # set by middleware

        target_user = get_object_or_404(User, id=user_id)

        membership, created = SystemMembership.objects.get_or_create(
            user=target_user,
            system_name=current_system,
            defaults={'system_role': new_role}
        )

        if not created:
            old_role = membership.system_role
            membership.system_role = new_role
            membership.save()

            Logs.objects.create(
                user=request.user,
                system_name=current_system,
                action='UPDATE',
                target_model='SystemMembership',
                target_id=membership.id,
                description=f"Changed role of user '{target_user.username}' from '{old_role}' to '{new_role}' in system '{current_system}'"
            )
        else:
            Logs.objects.create(
                user=request.user,
                system_name=current_system,
                action='CREATE',
                target_model='SystemMembership',
                target_id=membership.id,
                description=f"Assigned role '{new_role}' to user '{target_user.username}' in system '{current_system}'"
            )

        messages.success(request, f"Access level for user '{target_user.username}' updated to '{new_role}'.")
        return redirect("projectmanagement:pm_admin_dashboard") 

    return redirect("projectmanagement:pm_admin_dashboard")

@require_http_methods(["POST"])
def update_tos(request):
    """
    Update the Terms of Service for the current system.
    """

    current_system = request.current_system  # set by middleware

    # Get system membership for the current user
    system_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()

    allowed_roles = ['superadmin', 'admin']

    # Allow if superuser OR membership role is allowed
    if not (request.user.is_superuser or (system_membership and system_membership.system_role in allowed_roles)):
        return render(request, '404.html', status=404)

    tos_text = request.POST.get('tos_text', '')

    system = Systems.objects.get(name=current_system)
    system.terms_of_service = tos_text
    system.save()

    Logs.objects.create(
        user=request.user,
        system_name=current_system,
        action='UPDATE',
        target_model='Systems',
        target_id=system.id,
        description=f"Updated Terms of Service for system '{current_system}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    messages.success(request, "Terms of Service updated successfully.")
    return redirect("projectmanagement:pm_admin_dashboard") 


def system_logs(request):
    current_system = request.current_system  # set by middleware

    # Access control
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).exists():
        return render(request, '404.html', status=404)

    # ---- Get search query ----
    search_query = request.GET.get('search', '').strip()

    logs_qs = Logs.objects.filter(system_name=current_system)

    # 🔒 Hide superuser logs from non-superusers
    if not request.user.is_superuser:
        logs_qs = logs_qs.filter(
            Q(user__is_superuser=False) | Q(user__isnull=True)
        )

    # ---- Apply search filter ----
    if search_query:
        if request.user.is_superuser:
            logs_qs = logs_qs.filter(
                Q(user__username__icontains=search_query) |
                Q(action__icontains=search_query) |
                Q(target_model__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(hidden_description__icontains=search_query) |
                Q(ip_address__icontains=search_query) |
                Q(user_agent__icontains=search_query)
            )
        else:
            # For non-superusers, only search visible fields
            logs_qs = logs_qs.filter(
                Q(user__username__icontains=search_query) |
                Q(action__icontains=search_query) |
                Q(target_model__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(ip_address__icontains=search_query) |
                Q(user_agent__icontains=search_query)
            )

    logs_qs = logs_qs.order_by('-created_at')

    paginator = Paginator(logs_qs, 10)
    # Honor requested page even when searching
    page_number = request.GET.get('page') or 1
    logs = paginator.get_page(page_number)

    current_user_role = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).values_list('system_role', flat=True).first()

    context = {
        'logs': logs,
        'total_logs': logs_qs.count(),
        'current_system': current_system,
        'current_user_role': current_user_role,
        'search_query': search_query,
    }

    # ---- Handle AJAX requests ----
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logs_list_html = render_to_string(
            'projectmanagement/partials/admin/_system_logs_table.html',
            context,
            request=request
        )

        return JsonResponse({
            'logs_list_html': logs_list_html,
            'total_logs': logs_qs.count(),
            'search_query': search_query,
        })

    return render(
        request,
        'projectmanagement/pages/admin/system_logs.html',
        context
    )

@login_required
def save_addresses(request):
    if request.method != "POST":
        return redirect("projectmanagement:pm_settings")

    user = request.user

    # ------------------------
    # Handle Address 1 (home)
    # ------------------------
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
            system_name='core',
            action='CREATE',
            target_model='Address',
            target_id=home_address.id,
            description=f"Created home address for user '{user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    else:
        # Update existing home address
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
            system_name='core',
            action='UPDATE',
            target_model='Address',
            target_id=home_address.id,
            description=f"Updated home address for user '{user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    # ------------------------
    # Handle Address 2 (billing/secondary)
    # ------------------------
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
                system_name='core',
                action='CREATE',
                target_model='Address',
                target_id=billing_address.id,
                description=f"Created billing address for user '{user.username}'",
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
                system_name='core',
                action='UPDATE',
                target_model='Address',
                target_id=billing_address.id,
                description=f"Updated billing address for user '{user.username}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )

    return redirect("projectmanagement:pm_settings")

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    # Never allow deleting home address
    if address.type == 'home':
        return redirect('projectmanagement:pm_settings')

    if request.method == "POST":
        address.delete()

        Logs.objects.create(
            user=request.user,
            system_name='core',
            action='DELETE',
            target_model='Address',
            target_id=address.id,
            description=f"Deleted address for user '{request.user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    return redirect('projectmanagement:pm_settings')


@login_required
@require_POST
def upload_avatar(request):
    avatar = request.FILES.get("avatar")
    if avatar:
        # Delete old avatar if exists
        if request.user.avatar:
            request.user.avatar.delete(save=False)

        # Save new avatar
        request.user.avatar = avatar
        request.user.save()

        Logs.objects.create(
            user=request.user,
            system_name='core',
            action='UPDATE',
            target_model='User',
            target_id=request.user.id,
            description=f"Updated avatar for user '{request.user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )


    # Redirect back to profile page to refresh
        messages.success(request, "Avatar uploaded successfully.")
    return redirect('projectmanagement:pm_settings') 


@login_required
@require_POST
def remove_avatar(request):
    if request.user.avatar:
        request.user.avatar.delete(save=False)
        request.user.avatar = None
        request.user.save()
    
        Logs.objects.create(
            user=request.user,
            system_name='core',
            action='UPDATE',
            target_model='User',
            target_id=request.user.id,
            description=f"Removed avatar for user '{request.user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    messages.success(request, "Avatar removed successfully.")
    return redirect('projectmanagement:pm_settings') 

@login_required
@require_POST
def profile_update(request):
    user = request.user

    # Get form data
    first_name = request.POST.get("first_name", "").strip()
    middle_name = request.POST.get("middle_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    username = request.POST.get("username", "").strip()
    phone = request.POST.get("phone", "").strip()
    bio = request.POST.get("bio", "").strip()

    # Update user fields (properties will auto-encrypt)
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
        system_name='core',
        action='UPDATE',
        target_model='User',
        target_id=user.id,
        description=f"Updated profile for user '{user.username}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    messages.success(request, "Profile updated successfully.")
    return redirect("projectmanagement:pm_settings")

@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password1 = request.POST.get("new_password1")
        new_password2 = request.POST.get("new_password2")
        user = request.user

        # Check current password
        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("projectmanagement:pm_settings")  # redirect to your profile page

        # Check new passwords match
        if new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return redirect("projectmanagement:pm_settings")

        # Optional: validate password strength
        if len(new_password1) < 8:
            messages.error(request, "New password must be at least 8 characters long.")
            return redirect("projectmanagement:pm_settings")

        # Set new password
        user.set_password(new_password1)
        user.save()

        # Keep user logged in after password change
        update_session_auth_hash(request, user)

        messages.success(request, "Password changed successfully.")
        return redirect("projectmanagement:pm_settings")

    # fallback for GET requests
    return redirect("projectmanagement:pm_settings")

@login_required
def projects(request):
    """
    Display user's projects in a table format with search and pagination.
    """
    current_system = request.current_system

    # ---- Access control ----
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).exists():
        return render(request, '404.html', status=404)

    # ---- Get current user's role ----
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']

    # ---- Get search query ----
    search_query = request.GET.get('search', '').strip()

    # ---- Base queryset ----
    projects_qs = Project.objects.prefetch_related("tasks").all()
    
    # ---- Apply visibility scope based on user role ----
    if not is_admin_or_superadmin:
        # Regular users only see projects with tasks assigned to them
        projects_qs = projects_qs.filter(tasks__assigned_to=request.user).distinct()
    # Admins and superusers can see all projects

    # ---- Apply search filter ----
    if search_query:
        projects_qs = projects_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tasks__title__icontains=search_query)
        ).distinct()

    # Order by start date
    projects_qs = projects_qs.order_by('-start_date')

    # ---- Pagination ----
    paginator = Paginator(projects_qs, 5)  # 5 projects per page
    page_number = request.GET.get('page') or 1
    projects = paginator.get_page(page_number)

    # ---- Calculate progress for each project ----
    for project in projects:
        total_tasks = project.tasks.count()
        completed_tasks = project.tasks.filter(status='completed').count()
        project.progress_percentage = (completed_tasks * 100 // total_tasks) if total_tasks > 0 else 0

    current_user_role = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).values_list('system_role', flat=True).first()

    context = {
        'projects': projects,
        'projects_paginator': paginator,
        'total_projects': projects_qs.count(),
        'current_system': current_system,
        'current_user_role': current_user_role,
        'search_query': search_query,
        'now': now,
    }

    # ---- Handle AJAX requests ----
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        projects_table_html = render_to_string(
            'projectmanagement/partials/_projects_table.html',
            context,
            request=request
        )
        # Return HTML directly, not JSON for this simple case
        return HttpResponse(projects_table_html)

    # ---- Regular page load ----
    return render(
        request,
        'projectmanagement/pages/projects.html',
        context
    )

@login_required
@require_http_methods(["GET", "POST"])
def create_project(request):
    """Create a new project via modal"""
    current_system = request.current_system
    
    # Access control - only allow system members
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).exists():
        return render(request, '404.html', status=404)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            status = request.POST.get('status', 'planning')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            # Validate required fields
            if not name:
                messages.error(request, "Project name is required.")
                return render(request, 'projectmanagement/modals/add_project_modal.html', {})
            
            if not start_date or not end_date:
                messages.error(request, "Start date and end date are required.")
                return render(request, 'projectmanagement/modals/add_project_modal.html', {})

            project = Project.objects.create(
                name=name,
                description=description,
                status=status,
                start_date=start_date,
                end_date=end_date,
                created_by=request.user
            )

            Logs.objects.create(
                user=request.user,
                system_name='projectmanagement',
                action='CREATE',
                target_model='Project',
                target_id=project.id,
                description=f"Created project '{project.name}'",
                hidden_description=f"User '{request.user.username}' created project '{project.name}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )

            messages.success(request, f"Project '{project.name}' created successfully.")
            return redirect('projectmanagement:pm_projects')
        
        except ValidationError as e:
            messages.error(request, f"Invalid project data: {str(e)}")
            return render(request, 'projectmanagement/modals/add_project_modal.html', {})
        except Exception as e:
            messages.error(request, f"Error creating project: {str(e)}")
            return render(request, 'projectmanagement/modals/add_project_modal.html', {})
    
    if request.method == 'GET':
        return render(request, 'projectmanagement/modals/add_project_modal.html', {})

@login_required
@require_http_methods(["GET", "POST"])
def edit_project(request, project_id):
    """Edit a project via modal or AJAX"""
    project = get_object_or_404(Project, id=project_id)
    current_system = request.current_system
    
    # Check permissions
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    
    if not is_admin and project.created_by != request.user:

        return JsonResponse({'error': "You don't have permission to edit this project."}, status=403)
    
    if request.method == 'POST':
        project.name = request.POST.get('name', project.name)
        project.description = request.POST.get('description', project.description)
        project.status = request.POST.get('status', project.status)
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if start_date:
            project.start_date = start_date
        if end_date:
            project.end_date = end_date
        
        # Validate start date is before end date
        if project.start_date and project.end_date:
            from datetime import date
            # Convert to date objects if they're strings
            if isinstance(project.start_date, str):
                project_start_date = date.fromisoformat(project.start_date)
            else:
                project_start_date = project.start_date
                
            if isinstance(project.end_date, str):
                project_end_date = date.fromisoformat(project.end_date)
            else:
                project_end_date = project.end_date
            
            if project_start_date > project_end_date:
                error_message = f"Project start date ({project_start_date.strftime('%b %d, %Y')}) cannot be after end date ({project_end_date.strftime('%b %d, %Y')})."
                
                # Return JSON error for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    }, status=400)
                
                messages.error(request, error_message)
                return redirect('projectmanagement:pm_projects')
            
        project.save()
        
        Logs.objects.create(
            user=request.user,
            system_name='projectmanagement',
            action='UPDATE',
            target_model='Project',
            target_id=project.id,
            description=f"Updated project '{project.name}'",
            hidden_description=f"User '{request.user.username}' updated project '{project.name}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Project '{project.name}' updated successfully.",
                'project': {
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'status': project.status,
                    'start_date': project.start_date.isoformat() if hasattr(project.start_date, 'isoformat') else str(project.start_date),
                    'end_date': project.end_date.isoformat() if hasattr(project.end_date, 'isoformat') else str(project.end_date),
                }
            })
        
        messages.success(request, f"Project '{project.name}' updated successfully.")
        return redirect('projectmanagement:pm_projects')
    
    # GET request - return form data as JSON for modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'project': {
                'id': str(project.id),
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'start_date': project.start_date.isoformat(),
                'end_date': project.end_date.isoformat(),
            }
        })

@login_required
@require_http_methods(["POST"])
def delete_project(request, project_id):
    """Delete a project"""
    project = get_object_or_404(Project, id=project_id)
    current_system = request.current_system
    
    # Check permissions
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    
    if not is_admin and project.created_by != request.user:
        messages.error(request, "You don't have permission to delete this project.")
        return redirect('projectmanagement:pm_projects')
    
    project_name = project.name
    project.delete()
    
    Logs.objects.create(
        user=request.user,
        system_name='projectmanagement',
        action='DELETE',
        target_model='Project',
        target_id=project_id,
        description=f"Deleted project '{project_name}'",
        hidden_description=f"User '{request.user.username}' deleted project '{project_name}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, f"Project '{project_name}' deleted successfully.")
    return redirect('projectmanagement:pm_projects')

@login_required
@require_http_methods(["GET", "POST"])
def edit_task(request, task_id):
    """Edit a task via modal or AJAX"""
    task = get_object_or_404(Task, id=task_id)
    current_system = request.current_system
    
    # Check permissions
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    
    # Check if user is assigned to task
    is_assigned = task.assigned_to.filter(id=request.user.id).exists()
    
    if not is_admin and not is_assigned:
        return JsonResponse({'error': "You don't have permission to edit this task."}, status=403)
    
    if request.method == 'POST':
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.status = request.POST.get('status', task.status)
        task.priority = request.POST.get('priority', task.priority)
        due_date = request.POST.get('due_date')
        
        if due_date:
            task.due_date = due_date
        
        # Validate due date against project end date
        if task.due_date and task.project.end_date:
            from datetime import date
            # Convert to date object if it's a string
            if isinstance(task.due_date, str):
                task_due_date = date.fromisoformat(task.due_date)
            else:
                task_due_date = task.due_date
            
            if task_due_date > task.project.end_date:
                error_message = f"Task due date ({task_due_date.strftime('%b %d, %Y')}) cannot exceed project end date ({task.project.end_date.strftime('%b %d, %Y')})."
                
                # Return JSON error for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    }, status=400)
                
                messages.error(request, error_message)
                return redirect('projectmanagement:pm_projects')
            
        task.save()
        
        Logs.objects.create(
            user=request.user,
            system_name='projectmanagement',
            action='UPDATE',
            target_model='Task',
            target_id=task.id,
            description=f"Updated task '{task.title}' in project '{task.project.name}'",
            hidden_description=f"User '{request.user.username}' updated task '{task.title}' in project '{task.project.name}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            due_date_str = None
            if task.due_date:
                due_date_str = task.due_date.isoformat() if hasattr(task.due_date, 'isoformat') else str(task.due_date)
            
            return JsonResponse({
                'success': True,
                'message': f"Task '{task.title}' updated successfully.",
                'task': {
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'due_date': due_date_str,
                }
            })
        
        messages.success(request, f"Task '{task.title}' updated successfully.")
        return redirect('projectmanagement:pm_projects')
    
    # GET request - return form data as JSON for modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'task': {
                'id': str(task.id),
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'project_id': str(task.project.id),
                'project_name': task.project.name,
            }
        })
    
    return render(request, 'projectmanagement/pages/edit_task.html', {
        'task': task,
        'current_system': current_system,
    })

@login_required
@require_http_methods(["POST"])
def delete_task(request, task_id):
    """Delete a task"""
    task = get_object_or_404(Task, id=task_id)
    current_system = request.current_system
    
    # Check permissions
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    
    if not is_admin and task.assigned_to != request.user:
        messages.error(request, "You don't have permission to delete this task.")
        return redirect('projectmanagement:pm_projects')
    
    task_title = task.title
    project_name = task.project.name
    task.delete()
    
    Logs.objects.create(
        user=request.user,
        system_name='projectmanagement',
        action='DELETE',
        target_model='Task',
        target_id=task_id,
        description=f"Deleted task '{task_title}' from project '{project_name}'",
        hidden_description=f"User '{request.user.username}' deleted task '{task_title}' from project '{project_name}'",
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, f"Task '{task_title}' deleted successfully.")
    return redirect('projectmanagement:pm_projects')

@login_required
@require_http_methods(["POST"])
def complete_task(request, task_id):
    """Mark a task as completed"""
    task = get_object_or_404(Task, id=task_id)
    current_system = request.current_system
    
    # Check permissions
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    
    if not is_admin and task.assigned_to != request.user:
        messages.error(request, "You don't have permission to complete this task.")
        return redirect('projectmanagement:pm_projects')
    
    task.status = 'completed'
    task.save()
    
    Logs.objects.create(
        user=request.user,
        system_name='projectmanagement',
        action='UPDATE',
        target_model='Task',
        target_id=task.id,
        description=f"Marked task '{task.title}' as completed in project '{task.project.name}'",
        hidden_description=f"User '{request.user.username}' marked task '{task.title}' as completed in project '{task.project.name}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, f"Task '{task.title}' marked as completed.")
    return redirect('projectmanagement:pm_projects')

@login_required
@require_http_methods(["POST"])
def create_task(request, project_id):
    """Create a new task in a project"""
    project = get_object_or_404(Project, id=project_id)
    current_system = request.current_system
    
    # Check permissions - must be able to access the project
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    
    # Users can only create tasks in projects they're assigned to or if they're admin
    if not is_admin:
        if not project.tasks.filter(assigned_to=request.user).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': "You don't have permission to add tasks to this project."}, status=403)
            return redirect('projectmanagement:pm_projects')
    
    try:
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', 'todo')
        priority = request.POST.get('priority', 3)
        due_date = request.POST.get('due_date', None)
        
        # Validation
        if not title:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Task title is required'})
            messages.error(request, 'Task title is required')
            return redirect('projectmanagement:pm_projects')
        
        # Validate due date is within project date range
        if due_date:
            from datetime import date
            if isinstance(due_date, str):
                due_date_obj = date.fromisoformat(due_date)
            else:
                due_date_obj = due_date
            
            if due_date_obj < project.start_date:
                error_msg = f"Task due date cannot be before project start date ({project.start_date})"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('projectmanagement:pm_projects')
            
            if due_date_obj > project.end_date:
                error_msg = f"Task due date cannot exceed project end date ({project.end_date})"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('projectmanagement:pm_projects')
        
        # Create task
        task = Task.objects.create(
            project=project,
            title=title,
            description=description,
            status=status,
            priority=int(priority),
            due_date=due_date if due_date else None
        )
        
        # Create audit log
        Logs.objects.create(
            user=request.user,
            system_name='projectmanagement',
            action='CREATE',
            target_model='Task',
            target_id=task.id,
            description=f"Created task '{task.title}' in project '{project.name}'",
            hidden_description=f"User '{request.user.username}' created task '{task.title}' in project '{project.name}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Task '{task.title}' created successfully",
                'task_id': str(task.id)
            })
        
        messages.success(request, f"Task '{task.title}' created successfully")
        return redirect('projectmanagement:pm_projects')
        
    except ValueError as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': f'Invalid input: {str(e)}'})
        messages.error(request, f'Invalid input: {str(e)}')
        return redirect('projectmanagement:pm_projects')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': f'Error creating task: {str(e)}'})
        messages.error(request, f'Error creating task: {str(e)}')
        return redirect('projectmanagement:pm_projects')

@login_required
def api_users(request):
    """Get list of all active users for assignment."""
    try:
        current_system = request.current_system
        
        # Get users from current system
        system_members = SystemMembership.objects.filter(
            system_name=current_system
        ).select_related('user')
        
        users = [
            {
                'id': member.user.id,
                'username': member.user.username,
                'first_name': member.user.first_name,
                'last_name': member.user.last_name,
            }
            for member in system_members if member.user.is_active
        ]
        
        return JsonResponse({
            'success': True,
            'users': users
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_teams(request):
    """Get list of all teams for assignment."""
    try:
        teams = Team.objects.all().values('id', 'name')
        return JsonResponse({
            'success': True,
            'teams': list(teams)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_task_assignees(request, task_id):
    """Get currently assigned users and team for a task."""
    try:
        task = get_object_or_404(Task, id=task_id)
        
        # Get assigned users
        assigned_users = task.assigned_to.values_list('id', flat=True)
        assigned_team = task.assigned_team
        
        # Get team member IDs if a team is assigned
        team_member_ids = []
        if assigned_team:
            team_member_ids = list(assigned_team.members.values_list('id', flat=True))
        
        return JsonResponse({
            'success': True,
            'assigned_user_ids': list(assigned_users),
            'assigned_team_id': str(assigned_team.id) if assigned_team else None,
            'team_member_ids': team_member_ids,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def assign_task(request, task_id):
    """Assign task to users or team."""
    try:
        task = get_object_or_404(Task, id=task_id)
        project = task.project
        current_system = request.current_system
        
        # Check permissions
        user_membership = SystemMembership.objects.filter(
            user=request.user,
            system_name=current_system
        ).first()
        user_role = user_membership.system_role if user_membership else None
        is_authorized = (
            request.user.is_superuser or 
            user_role in ['admin', 'superadmin'] or 
            project.created_by_id == request.user.id
        )
        
        if not is_authorized:
            return JsonResponse({
                'success': False,
                'message': 'You do not have permission to assign this task'
            }, status=403)
        
        # Parse request data
        data = json.loads(request.body)
        assignment_type = data.get('assignment_type')
        
        if assignment_type == 'user':
            # Assign to individual users
            user_ids = data.get('user_ids', [])
            if not user_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No users selected'
                }, status=400)
            
            # Get users
            users = User.objects.filter(id__in=user_ids, is_active=True)
            if not users.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'No valid users found'
                }, status=400)
            
            # Clear existing assignments and add new ones
            task.assigned_to.clear()
            task.assigned_team = None
            task.assigned_to.set(users)
            task.save()
            
            # Create audit log
            user_names = ', '.join([u.username for u in users])
            Logs.objects.create(
                user=request.user,
                system_name='projectmanagement',
                action='UPDATE',
                target_model='Task',
                target_id=task.id,
                description=f"Assigned task '{task.title}' to users: {user_names}",
                hidden_description=f"User '{request.user.username}' assigned task '{task.title}' to users: {user_names}",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Task assigned to {len(users)} user(s)'
            })
        
        elif assignment_type == 'team':
            # Assign to team or clear team assignment
            team_id = data.get('team_id')

            # Handle explicit team unassignment
            if team_id in [None, '', 'unassign', 'none', 'null']:
                task.assigned_to.clear()
                task.assigned_team = None
                task.save()

                Logs.objects.create(
                    user=request.user,
                    system_name='projectmanagement',
                    action='UPDATE',
                    target_model='Task',
                    target_id=task.id,
                    description=f"Unassigned team from task '{task.title}'",
                    hidden_description=f"User '{request.user.username}' unassigned any team from task '{task.title}'",
                    ip_address=get_client_ip(request),
                    user_agent=get_user_agent(request),
                )

                return JsonResponse({
                    'success': True,
                    'message': 'Team unassigned from task'
                })

            team = get_object_or_404(Team, id=team_id)
            
            # Clear existing assignments and assign team
            task.assigned_to.clear()
            task.assigned_team = team
            task.save()
            
            # Create audit log
            Logs.objects.create(
                user=request.user,
                system_name='projectmanagement',
                action='UPDATE',
                target_model='Task',
                target_id=task.id,
                description=f"Assigned task '{task.title}' to team '{team.name}'",
                hidden_description=f"User '{request.user.username}' assigned task '{task.title}' to team '{team.name}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Task assigned to team {team.name}'
            })
        
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid assignment type'
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error assigning task: {str(e)}'
        }, status=500)

def teams(request):
    current_system = request.current_system

    # Access control: must be system member or superuser
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).exists():
        return render(request, '404.html', status=404)

    # Get current user's role
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']

    # Queries
    search_query = request.GET.get('search', '').strip()            # team search
    member_search_query = request.GET.get('member_search', '').strip()  # member search
    page_number = request.GET.get('page') or 1
    selected_team_id = request.GET.get('team')

    # Teams list with member count
    teams_qs = (
        Team.objects
        .annotate(member_count=Count('members'))
        .order_by('-created_at')
    )
    
    # Filter teams for non-admin users (only show teams they're assigned to)
    if not is_admin_or_superadmin:
        teams_qs = teams_qs.filter(members=request.user)
    
    if search_query:
        teams_qs = teams_qs.filter(name__icontains=search_query)

    paginator = Paginator(teams_qs, 25)
    teams_page = paginator.get_page(page_number)

    # Determine selected team (for non-admins default to their first team)
    selected_team = None
    if selected_team_id:
        selected_team = teams_qs.filter(id=selected_team_id).first()
    elif not is_admin_or_superadmin:
        selected_team = teams_qs.first()

    # Members list (team members if a team is selected, otherwise all users in system)
    if selected_team:
        members_qs = selected_team.members.all()
    else:
        if is_admin_or_superadmin:
            members_qs = User.objects.filter(
                systemmembership__system_name=current_system
            ).distinct()
        else:
            members_qs = User.objects.none()

    if member_search_query:
        members_qs = members_qs.filter(
            Q(username__icontains=member_search_query) |
            Q(email__icontains=member_search_query)
        )

    # Optimize query: order by username and email
    members = members_qs.order_by('username', 'email')

    # Fetch system roles for members
    member_roles = {
        m.user_id: m.system_role
        for m in SystemMembership.objects.filter(
            system_name=current_system,
            user__in=members
        )
    }

    # Users available to add to selected team (admins only)
    available_users = []
    if is_admin_or_superadmin and selected_team:
        available_users = User.objects.filter(
            systemmembership__system_name=current_system
        ).exclude(id__in=members.values_list('id', flat=True)).order_by('username')

    context = {
        'teams': teams_page,
        'teams_paginator': paginator,
        'selected_team': selected_team,
        'search_query': search_query,
        'member_search_query': member_search_query,
        'members': members,
        'member_roles': member_roles,
        'current_system': current_system,
        'current_user_role': user_role,
        'is_admin_or_superadmin': is_admin_or_superadmin,
        'available_users': available_users,
    }

    # AJAX: return only the relevant partial
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # If member_search param is present, return members list only
        if member_search_query or request.GET.get('search_type') == 'members':
            members_html = render_to_string(
                'projectmanagement/partials/_team_members_table.html' if selected_team else 'projectmanagement/partials/_teams_all_users_table.html',
                context,
                request=request
            )
            return HttpResponse(members_html)
        # Otherwise return teams list
        teams_html = render_to_string(
            'projectmanagement/partials/_teams_table.html',
            context,
            request=request
        )
        return HttpResponse(teams_html)

    return render(
        request,
        'projectmanagement/pages/teams.html',
        context
    )


@login_required
@require_http_methods(["POST"])
def add_team(request):
    current_system = request.current_system

    # Only admins/superadmins or superuser
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    if not is_admin_or_superadmin:
        return render(request, '404.html', status=404)

    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, "Team name is required.")
        return redirect('projectmanagement:pm_teams')

    try:
        team = Team.objects.create(name=name)
        
        Logs.objects.create(
            user=request.user,
            system_name='projectmanagement',
            action='CREATE',
            target_model='Team',
            target_id=team.id,
            description=f"Created team '{team.name}'",
            hidden_description=f"User '{request.user.username}' created team '{team.name}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        messages.success(request, f"Team '{name}' created successfully.")
    except IntegrityError:
        messages.error(request, f"Team '{name}' already exists.")

    return redirect('projectmanagement:pm_teams')


@login_required
@require_http_methods(["POST"])
def delete_team(request, team_id):
    current_system = request.current_system

    # Only admins/superadmins or superuser
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    if not is_admin_or_superadmin:
        return render(request, '404.html', status=404)

    team = get_object_or_404(Team, id=team_id)
    team_name = team.name
    team.delete()
    
    Logs.objects.create(
        user=request.user,
        system_name='projectmanagement',
        action='DELETE',
        target_model='Team',
        target_id=team_id,
        description=f"Deleted team '{team_name}'",
        hidden_description=f"User '{request.user.username}' deleted team '{team_name}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, f"Team '{team_name}' deleted successfully.")
    return redirect('projectmanagement:pm_teams')


@login_required
@require_http_methods(["POST"])
def add_team_user_placeholder(request, team_id):
    current_system = request.current_system

    # Only admins/superadmins or superuser
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    if not is_admin_or_superadmin:
        return render(request, '404.html', status=404)

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()

    if not name:
        messages.error(request, "Team name is required.")
        return redirect('projectmanagement:pm_teams')

    try:
        Team.objects.create(name=name, description=description)
        messages.success(request, f"Team '{name}' created successfully.")
    except IntegrityError:
        messages.error(request, f"Team '{name}' already exists.")

    return redirect('projectmanagement:pm_teams')


@login_required
@require_http_methods(["POST"])
def add_team_user(request, team_id):
    current_system = request.current_system

    # Only admins/superadmins or superuser
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    if not is_admin_or_superadmin:
        return render(request, '404.html', status=404)

    team = get_object_or_404(Team, id=team_id)
    user_id = request.POST.get('user_id')
    if not user_id:
        messages.error(request, "Select a user to add.")
        return redirect(f"{reverse('projectmanagement:pm_teams')}?team={team.id}")

    user = get_object_or_404(User, id=user_id)
    team.members.add(user)
    
    Logs.objects.create(
        user=request.user,
        system_name='projectmanagement',
        action='UPDATE',
        target_model='Team',
        target_id=team.id,
        description=f"Added user '{user.username}' to team '{team.name}'",
        hidden_description=f"User '{request.user.username}' added user '{user.username}' to team '{team.name}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, f"Added '{user.username}' to '{team.name}'.")
    return redirect(f"{reverse('projectmanagement:pm_teams')}?team={team.id}")


@login_required
@require_http_methods(["POST"])
def remove_team_user(request, team_id, user_id):
    current_system = request.current_system

    # Only admins/superadmins or superuser
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    if not is_admin_or_superadmin:
        return render(request, '404.html', status=404)

    team = get_object_or_404(Team, id=team_id)
    user = get_object_or_404(User, id=user_id)

    team.members.remove(user)
    
    Logs.objects.create(
        user=request.user,
        system_name='projectmanagement',
        action='UPDATE',
        target_model='Team',
        target_id=team.id,
        description=f"Removed user '{user.username}' from team '{team.name}'",
        hidden_description=f"User '{request.user.username}' removed user '{user.username}' from team '{team.name}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, f"Removed '{user.username}' from '{team.name}'.")
    return redirect(f"{reverse('projectmanagement:pm_teams')}?team={team.id}")


@login_required
@login_required
def calendar(request):
    """
    Display a calendar view with active and late projects and tasks.
    Supports week, month, and year views.
    """
    import calendar as cal_module
    from datetime import timedelta
    
    current_system = request.current_system
    
    # ---- Access control ----
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).exists():
        return redirect("projectmanagement:pm_dashboard")
    
    # ---- Get current user's role ----
    user_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()
    user_role = user_membership.system_role if user_membership else None
    is_admin_or_superadmin = request.user.is_superuser or user_role in ['admin', 'superadmin']
    
    # ---- Base querysets ----
    projects = Project.objects.prefetch_related("tasks")
    all_tasks = (
        Task.objects
        .select_related("project")
        .prefetch_related("assigned_to", "assigned_team__members")
    )
    
    # ---- Apply visibility scope based on user role ----
    if not is_admin_or_superadmin:
        # Non-admins only see projects they created or are in the team
        projects = projects.filter(
            Q(created_by=request.user) | Q(team__members=request.user)
        ).distinct()
        # Non-admins only see tasks they are assigned to
        all_tasks = all_tasks.filter(
            Q(assigned_to=request.user) | Q(assigned_team__members=request.user)
        ).distinct()
    
    # ---- Get current date ----
    now = timezone.now()
    today = now.date()
    
    # ---- Get view mode ----
    view = request.GET.get('view', 'month')  # week, month, or year
    
    # ---- Get calendar month/year from query params ----
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # ---- Calculate date ranges based on view mode ----
    if view == 'week':
        # Get week start date (Monday)
        week_start_str = request.GET.get('week_start')
        if week_start_str:
            week_start = timezone.datetime.strptime(week_start_str, '%Y-%m-%d').date()
        else:
            # Always use the current week (most recent)
            week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        first_day = week_start
        last_day = week_end
        
        # Generate week days for template
        week_days = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for i in range(7):
            current_day = week_start + timedelta(days=i)
            week_days.append((current_day, day_names[i]))
        
        # Calculate previous/next week
        prev_week_start = week_start - timedelta(days=7)
        next_week_start = week_start + timedelta(days=7)
        prev_year, prev_month = prev_week_start.year, prev_week_start.month
        next_year, next_month = next_week_start.year, next_week_start.month
        
    elif view == 'year':
        # Year view
        first_day = timezone.datetime(year, 1, 1).date()
        last_day = timezone.datetime(year, 12, 31).date()
        
        # Generate year calendars for each month
        year_calendars = []
        month_names = {i: cal_module.month_name[i] for i in range(1, 13)}
        for m in range(1, 13):
            raw_calendar_grid = cal_module.monthcalendar(year, m)
            month_cal = []
            for week in raw_calendar_grid:
                week_with_dates = []
                for day in week:
                    if day != 0:
                        date_obj = timezone.datetime(year, m, day).date()
                        week_with_dates.append({'day': day, 'date': date_obj})
                    else:
                        week_with_dates.append({'day': 0, 'date': None})
                month_cal.append(week_with_dates)
            year_calendars.append((m, month_cal))
        
        # Calculate previous/next year
        prev_year = year - 1
        next_year = year + 1
        prev_month = 12
        next_month = 1
        
    else:  # month (default)
        view = 'month'
        first_day = timezone.datetime(year, month, 1).date()
        last_day = timezone.datetime(year, month, cal_module.monthrange(year, month)[1]).date()
        
        # Get calendar grid for the month - enhanced with date objects
        raw_calendar_grid = cal_module.monthcalendar(year, month)
        calendar_grid = []
        for week in raw_calendar_grid:
            week_with_dates = []
            for day in week:
                if day != 0:
                    date_obj = timezone.datetime(year, month, day).date()
                    week_with_dates.append({'day': day, 'date': date_obj})
                else:
                    week_with_dates.append({'day': 0, 'date': None})
            calendar_grid.append(week_with_dates)
        
        # Calculate previous/next month
        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year
        
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
        
        month_name = cal_module.month_name[month]
    
    # ---- Get active projects (within date range) ----
    active_projects = projects.filter(
        start_date__lte=now.date(),
        end_date__gte=now.date()
    ).exclude(status='completed').exclude(status='cancelled')
    
    # ---- Get late projects (ended before today) ----
    late_projects = projects.filter(
        end_date__lt=now.date()
    ).exclude(status='completed').exclude(status='cancelled')
    
    # ---- Get active tasks (not completed, due date >= today) ----
    active_tasks = all_tasks.exclude(status='completed').filter(
        due_date__gte=now.date()
    )
    
    # ---- Get late/overdue tasks ----
    overdue_tasks = all_tasks.exclude(status='completed').filter(
        due_date__lt=now.date()
    )
    
    # ---- Calculate total counts (combining active and late) ----
    total_projects = active_projects.count() + late_projects.count()
    total_tasks = active_tasks.count() + overdue_tasks.count()
    
    # ---- Build calendar events dictionary ----
    calendar_events = {}
    
    # Add active projects
    for project in active_projects:
        for date in (project.start_date + timedelta(days=i) 
                    for i in range((project.end_date - project.start_date).days + 1)):
            if first_day <= date <= last_day:
                if date not in calendar_events:
                    calendar_events[date] = {'projects': [], 'tasks': []}
                calendar_events[date]['projects'].append({
                    'id': project.id,
                    'name': project.name,
                    'status': 'active',
                    'type': 'project'
                })
    
    # Add late projects
    for project in late_projects:
        if project.end_date >= first_day:
            date = min(project.end_date, last_day)
            if first_day <= date <= last_day:
                if date not in calendar_events:
                    calendar_events[date] = {'projects': [], 'tasks': []}
                # Check if already added as active
                if not any(p['id'] == project.id for p in calendar_events[date]['projects']):
                    calendar_events[date]['projects'].append({
                        'id': project.id,
                        'name': project.name,
                        'status': 'late',
                        'type': 'project'
                    })
    
    # Add active tasks
    for task in active_tasks:
        if first_day <= task.due_date <= last_day:
            if task.due_date not in calendar_events:
                calendar_events[task.due_date] = {'projects': [], 'tasks': []}
            calendar_events[task.due_date]['tasks'].append({
                'id': task.id,
                'title': task.title,
                'project': task.project.name,
                'status': 'active',
                'priority': task.priority,
                'type': 'task'
            })
    
    # Add overdue tasks
    for task in overdue_tasks:
        if first_day <= task.due_date <= last_day:
            if task.due_date not in calendar_events:
                calendar_events[task.due_date] = {'projects': [], 'tasks': []}
            calendar_events[task.due_date]['tasks'].append({
                'id': task.id,
                'title': task.title,
                'project': task.project.name,
                'status': 'overdue',
                'priority': task.priority,
                'type': 'task'
            })
    
    # ---- Build context ----
    context = {
        'calendar_events': calendar_events,
        'year': year,
        'month': month,
        'today': today,
        'view': view,
        'active_projects': active_projects,
        'late_projects': late_projects,
        'active_tasks': active_tasks,
        'overdue_tasks': overdue_tasks,
        'total_projects': total_projects,
        'total_tasks': total_tasks,
        'total_late_projects': late_projects.count(),
        'total_overdue_tasks': overdue_tasks.count(),
        'current_system': current_system,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
    }
    
    # Add view-specific context
    if view == 'month':
        context['calendar_grid'] = calendar_grid
        context['month_name'] = month_name
    elif view == 'week':
        context['week_days'] = week_days
        context['week_start'] = week_start
        context['week_end'] = week_end
        context['prev_week_start'] = prev_week_start.strftime('%Y-%m-%d')
        context['next_week_start'] = next_week_start.strftime('%Y-%m-%d')
    elif view == 'year':
        context['year_calendars'] = year_calendars
        context['month_names'] = {i: cal_module.month_name[i] for i in range(1, 13)}
    
    return render(request, 'projectmanagement/pages/calendar.html', context)