from django.shortcuts import render, redirect,  get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from .models import Project
from core.models import Logs
from core.utils import get_client_ip, get_user_agent, decrypt, encrypt
from django.contrib import messages
from core.models import SystemMembership
from django.views.decorators.http import require_POST, require_http_methods

User = get_user_model()


def dashboard(request):
    current_system = request.current_system  # set by middleware

    # Superuser bypass
    if not request.user.is_superuser and not SystemMembership.objects.filter(
        user=request.user, system_name=current_system
    ).exists():
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    projects = Project.objects.all()

    current_user_role = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).values_list('system_role', flat=True).first()

    return render(
        request,
        'projectmanagement/pages/dashboard.html',
        {
            'projects': projects,
            'systems': systems,
            'current_user_role': current_user_role,
            'current_system': current_system,
        }
    )


def admin_dashboard(request):
    current_system = request.current_system  # set by middleware

    users_qs = (
        User.objects
        .filter(systemmembership__system_name=current_system)
        .exclude(id=request.user.id)
        .exclude(systemmembership__system_role='admin') 
        .distinct()
        .order_by('-date_joined')
    )

    # Fetch roles for users in this system
    system_roles = {
        m.user_id: m.system_role
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
        description=f"Deactivated user '{user.username}'"
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
        description=f"Activated user '{user.username}'"
    )
    
    return redirect("projectmanagement:pm_admin_dashboard") 

def delete_user(request, user_id):
    """
    Delete a user by their ID.
    Only accessible by superusers.
    """
    if not request.user.is_superuser:
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