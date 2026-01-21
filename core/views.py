from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import get_user_model, update_session_auth_hash
from .models import CustomUser, Logs, Address, SystemMembership
from .utils import get_client_ip, get_user_agent, encrypt, decrypt
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import Group
from django.utils import timezone
from .forms import LoginForm
from django.contrib import messages
import random, uuid
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator
from django.db import IntegrityError

User = get_user_model()

def core_register(request, system_name):
    User = get_user_model()

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        terms_accepted = request.POST.get('terms_accepted')
        avatar = request.FILES.get('avatar')
        avatar_url = request.POST.get('avatar_url')

        # Validate terms
        if terms_accepted != 'true':
            messages.error(request, "You must accept the Terms and Conditions to register.")
            return render(request, 'core/pages/register.html', {'error': 'Accept the Terms and Conditions', 'system_name': system_name})

        if not username or not password:
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'core/pages/register.html', {'error': 'Fill all required fields', 'system_name': system_name})
    
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'core/pages/register.html', {'error': 'Username already exists', 'system_name': system_name})

        # Create the user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            avatar_url=avatar_url
        )

        if avatar:
            user.avatar = avatar
            user.save()

        # Log registration
        Logs.objects.create(
            user=user,
            system_name=system_name,
            action='REGISTER',
            target_model='User',
            target_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            description=f"User '{username}' registered for {system_name}"
        )

        # Assign system membership
        SystemMembership.objects.create(user=user, system_name=system_name, system_role='member')

        messages.success(request, "Registration successful. Please log in.")

        # --- Redirect to system-specific login like core_logout ---
        if system_name != 'core':
            messages.info(request, f"You can now log in.")
            return redirect(f'/{system_name}/login/')
        return redirect('core:core_login')

    # GET request: just render form
    return render(request, 'core/pages/register.html', {'system_name': system_name})

def core_login(request, system_name=None):
    User = get_user_model()
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        user = authenticate(request, username=username, password=password)

        if not user:
            form.add_error(None, "Invalid username or password.")
            return render(request, "core/pages/login.html", {"form": form, "system_name": system_name})

        # Superuser-only check for /login
        if not system_name and not user.is_superuser:
            messages.error(request, "Oopps! You do not have access to the core system.")
            return redirect('core:core_login')

        login(request, user)

        # Fetch systems the user belongs to
        memberships = SystemMembership.objects.filter(user=user)
        accessible_systems = [
            {"url": m.system_name, "name": m.system_name.title(), "role": m.system_role} 
            for m in memberships
        ]

        # Helper: determine dashboard URL
        def get_dashboard_url(system):
            if system.get("role") == "admin":
                return f"/{system['url']}/admin/dashboard/"
            if system["url"] == "core":
                return "/dashboard/"
            return f"/{system['url']}/dashboard/"

        # 1. Login via specific system URL
        if system_name and any(s['url'] == system_name for s in accessible_systems):
            target_system = next(s for s in accessible_systems if s['url'] == system_name)
            Logs.objects.create(
                user=user,
                target_model="User",
                system_name=system_name,
                target_id=user.id,
                action="LOGIN",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                description=f"User logged in for {system_name}"
            )
            messages.success(request, f"Welcome {user.username}!")
            return redirect(get_dashboard_url(target_system))

        # 2. User has only one system
        elif len(accessible_systems) == 1:
            target_system = accessible_systems[0]
            Logs.objects.create(
                user=user,
                target_model="User",
                system_name=target_system['url'],
                target_id=user.id,
                action="LOGIN",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                description=f"User logged in for {target_system['url']}"
            )
            return redirect(get_dashboard_url(target_system))

        # 3. Multiple systems, let them choose
        elif len(accessible_systems) > 1:
            request.session["accessible_systems"] = accessible_systems
            messages.info(request, "Please select a system to continue.")
            return redirect("core:system_selection")

        # 4. No systems (only possible for superusers)
        elif user.is_superuser:
            system_names = [
                'core',
                'projectmanagement',
                'librarymanagement',
                'informationmanagement',
                'inventorymanagement',
                'performanceevaluation',
                'communityextensionservices',
            ]
            for sys_name in system_names:
                SystemMembership.objects.get_or_create(
                    user=user,
                    system_name=sys_name,
                    defaults={'system_role': 'superadmin'}
                )
            return redirect('core:system_selection')

        else:
            messages.error(request, "You are not assigned to any system.")
            return redirect('core:core_login')

    return render(request, "core/pages/login.html", {"form": form, "system_name": system_name})


def system_selection(request):
    systems = request.session.get('accessible_systems')
    
    if not systems and not request.user.is_superuser:
        messages.error(request, "No Access.")
        return redirect('core:core_login')

    # --- Ensure 'core' is always first ---
    systems = sorted(
        systems,
        key=lambda s: 0 if s.get('url') == 'core' else 1
    )

    # Persist the ordered list (important for POST validation consistency)
    request.session['accessible_systems'] = systems

    if request.method == 'POST':
        selected_system = request.POST.get('system')

        # Verify the user has access to this system
        if any(s['url'] == selected_system for s in systems):
            Logs.objects.create(
                user=request.user,
                target_model="User",
                system_name=selected_system,
                target_id=request.user.id,
                action="LOGIN",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                description=f"User logged in for {selected_system}"
            )

            # Clear selection list after use
            del request.session['accessible_systems']
            request.session['current_system'] = selected_system

            if selected_system == 'core':
                return redirect('core:core_dashboard')
            return redirect(f"/{selected_system}")

        messages.error(request, "Invalid system selection.")
        return redirect('core:core_login')

    return render(
        request,
        'core/pages/system_selection.html',
        {'systems': systems}
    )

def core_logout(request, system_name=None):
    # Resolve current system
    current_system = system_name or request.session.get('current_system', 'core')

    # Capture user state BEFORE logout
    is_admin = request.user.is_authenticated and request.user.is_superuser

    # Log logout action
    if request.user.is_authenticated:
        Logs.objects.create(
            user=request.user,
            target_model="User",
            system_name=current_system,
            target_id=request.user.id,
            action='LOGOUT',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            description=f'User logged out from {current_system}'
        )

    # Logout and clear session
    auth_logout(request)
    request.session.flush()

    messages.info(request, "You have been logged out.")

    # Admins ALWAYS go to core
    if is_admin:
        return redirect('core:core_login')

    # Non-core systems redirect to their own login
    if current_system != 'core':
        return redirect(f'/{current_system}/login/')

    return redirect('core:core_login')

def dashboard(request):
    # Get accessible systems from session
    systems = request.session.get('accessible_systems', [])
    
    # Get all users except the current user
    users_qs = User.objects.exclude(id=request.user.id).order_by('-date_joined')
    
    paginator = Paginator(users_qs, 10)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    return render(
        request,
        'core/pages/dashboard.html',
        {
            'users': users,
            'total_users': users_qs.count(),
            'systems': systems,
        }
    )


@user_passes_test(lambda u: u.is_superuser)
def manage_user_systems(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    if request.user == target_user:
        return render(request, '404.html', status=404)

    all_systems = (
        SystemMembership.objects
        .values_list('system_name', flat=True)
        .distinct()
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        old_memberships = {
            m.system_name: m
            for m in target_user.systemmembership_set.all()
        }
        old_systems = set(old_memberships.keys())

        # CLEAR ALL FEATURE
        if action == 'clear':
            target_user.systemmembership_set.all().delete()

            for system_name in old_systems:
                Logs.objects.create(
                    user=request.user,
                    system_name='core',
                    action='UPDATE',
                    target_model='User',
                    target_id=target_user.id,
                    description=f"Cleared user '{target_user.username}' from system '{system_name}'"
                )

            return redirect('core:manage_user_systems', user_id=user_id)

        # NORMAL SAVE FLOW
        selected_systems = set(request.POST.getlist('systems'))

        # REMOVE systems
        for system_name in old_systems - selected_systems:
            old_memberships[system_name].delete()
            Logs.objects.create(
                user=request.user,
                system_name='core',
                action='UPDATE',
                target_model='User',
                target_id=target_user.id,
                description=f"Removed user '{target_user.username}' from system '{system_name}'"
            )

        # ADD or UPDATE systems + roles
        for system_name in selected_systems:
            role = request.POST.get(f'role_{system_name}', 'admin')

            if system_name in old_memberships:
                membership = old_memberships[system_name]

                if membership.system_role != role:
                    membership.system_role = role
                    membership.save(update_fields=['system_role'])

                    Logs.objects.create(
                        user=request.user,
                        system_name='core',
                        action='UPDATE',
                        target_model='User',
                        target_id=target_user.id,
                        description=(
                            f"Updated role for user '{target_user.username}' "
                            f"in system '{system_name}' to '{role}'"
                        )
                    )
            else:
                SystemMembership.objects.create(
                    user=target_user,
                    system_name=system_name,
                    system_role='admin'
                )

                Logs.objects.create(
                    user=request.user,
                    system_name='core',
                    action='UPDATE',
                    target_model='User',
                    target_id=target_user.id,
                    description=(
                        f"Added user '{target_user.username}' "
                        f"to system '{system_name}' with role '{role}'"
                    )
                )

        return redirect('core:core_dashboard')

    # GET
    user_systems = target_user.systemmembership_set.values_list(
        'system_name', flat=True
    )

    system_roles = {
        m.system_name: m.system_role
        for m in target_user.systemmembership_set.all()
    }

    return render(
        request,
        'core/pages/manage_user_systems.html',
        {
            'target_user': target_user,
            'all_systems': all_systems,
            'user_systems': user_systems,
            'system_roles': system_roles,
        }
    )


@require_http_methods(["POST"])
def deactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    
    Logs.objects.create(
        user=request.user,
        system_name='core',
        action='UPDATE',
        target_model='User',
        target_id=user.id,  # Fixed: was target_user.id
        description=f"Deactivated user '{user.username}'"
    )
    
    return redirect("core:core_dashboard")  # Changed to redirect to dashboard


@require_http_methods(["POST"])
def activate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    
    Logs.objects.create(
        user=request.user,
        system_name='core',
        action='UPDATE',
        target_model='User',
        target_id=user.id,  # Fixed: was target_user.id
        description=f"Activated user '{user.username}'"
    )
    
    return redirect("core:core_dashboard")  # Changed to redirect to dashboard

def core_delete_user(request, user_id):
    """
    Delete a user by their ID.
    Only accessible by superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('core:core_dashboard')

    target_user = get_object_or_404(User, id=user_id)

    if request.user == target_user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('core:core_dashboard')

    if request.method == 'POST':
        username = target_user.username
        target_user.delete()

        Logs.objects.create(
            user=request.user,
            system_name='core',
            action='DELETE',
            target_model='User',
            target_id=user_id,
            description=f"Deleted user '{username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        Logs.objects.create(
            user=request.user,
            system_name='core',
            action='DELETE',
            target_model='SystemMembership',
            target_id=None,
            description=f"Deleted all system memberships for user '{username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, f"User '{username}' has been deleted.")
        return redirect('core:core_dashboard')

    # If not POST, redirect to dashboard
    return redirect('core:core_dashboard')

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

    # Update user fields
    if first_name:
        user.first_name = first_name
    user.middle_name = middle_name  # middle name can be blank
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
# ===========
# # ADMIN CREATION VIEW
# ===========

@user_passes_test(lambda u: u.is_superuser)
def create_system_admin(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        system_access = request.POST.getlist('system_access')

        # Validation
        if not username or not email or not password1:
            messages.error(request, "Please fill in all required fields.")
            return redirect('core:core_dashboard')

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('core:core_dashboard')

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('core:core_dashboard')

        if not system_access:
            messages.error(request, "Please select at least one system for the admin.")
            return redirect('core:core_dashboard')

        # Friendly pre-checks (UX)
        if User.objects.filter(username=username).exists():
            messages.info(request, f"Username '{username}' already exists.")
            return redirect('core:core_dashboard')

        if User.objects.filter(email=email).exists():
            messages.info(request, f"Email '{email}' is already registered.")
            return redirect('core:core_dashboard')

        try:
            admin_user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                is_staff=True,
                is_active=True
            )

            Logs.objects.create(
                user=request.user,
                system_name='core',
                action='CREATE',
                target_model='User',
                target_id=admin_user.id,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                description=f"Created superadmin user '{username}'"
            )

            for system_name in system_access:
                membership = SystemMembership.objects.create(
                    user=admin_user,
                    system_name=system_name.lower(),
                    system_role='superadmin'
                )

                Logs.objects.create(
                    user=request.user,
                    system_name='core',
                    action='CREATE',
                    target_model='SystemMembership',
                    target_id=membership.id,
                    ip_address=get_client_ip(request),
                    user_agent=get_user_agent(request),
                    description=(
                        f"Assigned superadmin '{username}' "
                        f"to system '{system_name}' with superadmin role"
                    )
                )

            messages.success(
                request,
                f"Admin user '{username}' created successfully."
            )
            return redirect('core:core_dashboard')

        except IntegrityError:
            # Race-condition safe fallback
            messages.info(
                request,
                "A user with this username or email already exists."
            )
            return redirect('core:core_dashboard')

        except Exception:
            # True unexpected failure
            messages.error(
                request,
                "An unexpected error occurred while creating the admin user."
            )
            return redirect('core:core_dashboard')

    return redirect('core:core_dashboard')