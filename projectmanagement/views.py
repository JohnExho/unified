from django.shortcuts import render, redirect,  get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from .models import Project, Task
from core.models import Logs, SystemMembership, Systems
from core.utils import get_client_ip, get_user_agent, decrypt, encrypt
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required

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

    # ---- Base querysets ----
    projects = Project.objects.prefetch_related("tasks")
    all_tasks = Task.objects.select_related("assigned_to", "project")

    # ---- Apply visibility scope ----
    if not request.user.is_superuser:
        all_tasks = all_tasks.filter(assigned_to=request.user)
        projects = projects.filter(tasks__assigned_to=request.user).distinct()

    # ---- Time-aware project states ----
    active_projects = projects.filter(
        start_date__lte=now,
        end_date__gte=now
    )

    past_projects = projects.filter(
        end_date__lt=now
    )

    active_projects_count = active_projects.count()

    # ---- Time-aware task states ----
    active_tasks = all_tasks.exclude(
        status='completed'
    ).filter(
        due_date__gte=now
    )

    overdue_tasks = all_tasks.exclude(
        status='completed'
    ).filter(
        due_date__lt=now
    )

    active_tasks_count = active_tasks.count()

    # ---- Assignment stats ----
    if request.user.is_superuser:
        assigned_projects_count = projects.count()
        assigned_tasks_count = all_tasks.count()
    else:
        assigned_projects_count = active_projects.count()
        assigned_tasks_count = all_tasks.count()

    # ---- Late/Overdue stats ----
    late_projects_count = past_projects.count()
    late_tasks_count = overdue_tasks.count()

    # ---- Kanban buckets ----
    todo_tasks = all_tasks.filter(
        status='todo'
    )

    in_progress_tasks = all_tasks.filter(
        status='in_progress'
    )

    completed_tasks = all_tasks.filter(
        status='completed'
    )

    return render(
        request,
        'projectmanagement/pages/dashboard.html',
        {
            'projects': projects,
            'current_system': current_system,
            'now': now,
            # Stats
            'active_projects_count': active_projects_count,
            'active_tasks_count': active_tasks_count,
            'assigned_projects_count': assigned_projects_count,
            'assigned_tasks_count': assigned_tasks_count,
            'late_projects_count': late_projects_count,
            'late_tasks_count': late_tasks_count,

            # Kanban
            'todo_tasks': todo_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks': completed_tasks,

            # Optional future use
            'overdue_task_ids': set(overdue_tasks.values_list('id', flat=True)),
            'past_projects': past_projects,
        }
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

    # Fetch roles for users in this system
    system_roles = {
            m.user_id: (m.system_role, ROLE_LABELS.get(m.system_role, m.system_role.title()))
        for m in SystemMembership.objects.filter(
            system_name=current_system,
            user__in=users_qs
        )
    }

    paginator = Paginator(users_qs, 10)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    current_user_role = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).values_list('system_role', flat=True).first()

    return render(
        request,
        'projectmanagement/pages/admin/dashboard.html',
        {
            'users': users,
            'total_users': users_qs.count(),
            'current_system': current_system,
            'system_roles': system_roles,
            'current_user_role': current_user_role,
            'tos_text': tos_text,  # Pass TOS to template
        }
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
            description=f"Deleted user '{username}'",
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

    # Superuser bypass
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user, system_name=current_system
    ).exists():
        return render(request, '404.html', status=404)

    logs_qs = Logs.objects.filter(system_name=current_system).order_by('-created_at')

    paginator = Paginator(logs_qs, 10)
    page_number = request.GET.get('page')
    logs = paginator.get_page(page_number)


    current_user_role = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).values_list('system_role', flat=True).first()


    return render(
        request,
        'projectmanagement/pages/admin/system_logs.html',
        {
            'logs': logs,
            'total_logs': logs_qs.count(),
            'current_system': current_system,
            'current_user_role': current_user_role,
        }
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
            description=f"Deleted address for user '{user.username}'",
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
