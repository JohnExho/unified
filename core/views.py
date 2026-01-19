from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import get_user_model, update_session_auth_hash
from .models import AdminLog, Address
from .utils import get_client_ip, get_user_agent, encrypt, decrypt
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import Group
from django.utils import timezone
from .forms import LoginForm
from django.contrib import messages
import random, uuid
from django.http import JsonResponse
from django.views.decorators.http import require_POST


User = get_user_model()

# Map systems to their login URLs
SYSTEM_PERMISSION_MAP = {
    'users': ('core.access_users_system', 'Users Access Management'),
    'projectmanagement/dashboard': ('projectmanagement.access_project_management_system', 'Project Management'),
    'library/dashboard': ('librarymanagement.access_library_management_system', 'Library Management'),
    'inventory/dashboard': ('inventorymanagement.access_inventory_management_system', 'Inventory Management'),
    'communityextensionservices/dashboard': ('communityextensionservices.access_community_extension_services_system', 'Community Extension Services'),
    'informationmanagement/dashboard': ('informationmanagement.access_information_dashboard_system', 'Information Management'),
    'performanceevaluation/dashboard': ('performanceevaluation.access_performance_evaluation_system', 'Performance Evaluation'),
}



def core_register(request):
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
        
        # Validate terms acceptance
        if terms_accepted != 'true':
            return render(request, 'core/register.html', {
                'error': 'You must accept the Terms and Conditions to register.'
            })
        
        if not username or not password:
            return render(request, 'core/register.html', {
                'error': 'Please fill out all required fields.'
            })
        
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            return render(request, 'core/register.html', {
                'error': 'Username already exists.'
            })
        
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            avatar_url=avatar_url
        )
        
        # Set avatar if provided
        if avatar:
            user.avatar = avatar
            user.save()
        
        # Log registration
        AdminLog.objects.create(
            user=user,
            system_name='core',
            action='REGISTER',
            target_model='User',
            target_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            description=f"User '{username}' registered and accepted terms"
        )
        
        messages.success(request, "Registration successful. Please log in.")
        return redirect('core:core_login')

    messages.error(request, "Registration failed. Please try again.")
    return render(request, 'core/register.html')

def core_login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                
                AdminLog.objects.create(
                    user=user,
                    target_model="User",
                    target_id=user.id,
                    action="LOGIN",
                    ip_address=get_client_ip(request),
                    user_agent=get_user_agent(request),
                    description="Admin logged in",
                )
                
                # System routing
                accessible_systems = [
                    {"url": system, "name": name}
                    for system, (perm, name) in SYSTEM_PERMISSION_MAP.items()
                    if user.has_perm(perm)
                ]

                if len(accessible_systems) == 1:
                    messages.success(request, f"Welcome to {accessible_systems[0]['name']}!")
                    return redirect(f"/{accessible_systems[0]['url']}/")
                if len(accessible_systems) > 1:
                    request.session["accessible_systems"] = accessible_systems
                    return redirect("core:system_selection")

                return redirect("/404/")
            else:
                form.add_error(None, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, "core/login.html", {"form": form})


def system_selection(request):
    systems = request.session.get('accessible_systems')

    if not systems:
        return redirect('core:core_login')
    
    # redundant logging removed
    # AdminLog.objects.create(
    #     user=request.user,
    #     system_name='core',
    #     action='OTHER',
    #     description='Viewed system selection page'
    # )

    return render(request, 'core/system_selection.html', {'systems': systems})



def core_logout(request):
    if request.user.is_authenticated:
        AdminLog.objects.create(
            user=request.user,
            target_model="User",
            target_id=request.user.id,
            action='LOGOUT',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            description='User logged out'
        )

    auth_logout(request)
    return redirect('core:core_login')


def user_list(request):
    systems = request.session.get('accessible_systems', [])
    users = User.objects.exclude(id=request.user.id).order_by('username')
    return render(request, 'core/user_list.html', {'users': users, 'systems': systems})


@user_passes_test(lambda u: u.is_superuser)
def manage_user_groups(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    all_groups = Group.objects.all()

    if request.user == target_user:
        return render(request, '404.html', status=404)

    if request.method == 'POST':
        action = request.POST.get('action')

        old_groups = set(target_user.groups.values_list('name', flat=True))

        # CLEAR ALL FEATURE
        if action == 'clear':
            target_user.groups.clear()

            for g in old_groups:
                AdminLog.objects.create(
                    user=request.user,
                    system_name='core',
                    action='UPDATE',
                    target_model='User',
                    target_id=target_user.id,
                    description=f"Cleared user from group '{g}'"
                )

            return redirect('core:manage_user_groups', user_id=user_id)

        # NORMAL SAVE FLOW
        selected_groups = request.POST.getlist('groups')
        new_groups = set(selected_groups)

        target_user.groups.set(
            Group.objects.filter(name__in=new_groups)
        )

        added = new_groups - old_groups
        removed = old_groups - new_groups

        for g in added:
            AdminLog.objects.create(
                user=request.user,
                system_name='core',
                action='UPDATE',
                target_model='User',
                target_id=target_user.id,
                description=f"Added user to group '{g}'"
            )

        for g in removed:
            AdminLog.objects.create(
                user=request.user,
                system_name='core',
                action='UPDATE',
                target_model='User',
                target_id=target_user.id,
                description=f"Removed user from group '{g}'"
            )

        return redirect('core:user_list')

    return render(
        request,
        'core/manage_user_groups.html',
        {
            'target_user': target_user,
            'groups': all_groups,
        }
    )


def deactivate_user(request, user_id):
    if request.method == "POST":
        user = User.objects.get(id=user_id)
        user.is_active = False
        # user.groups.clear()  # Optionally clear groups on deactivation
        AdminLog.objects.create(
            user=request.user,
            system_name='core',
            action='UPDATE',
            target_model='User',
            target_id=target_user.id,
            description=f"Deactivated user '{user.username}'"
        )
        user.save()
    return redirect("core:user_list")


def activate_user(request, user_id):
    if request.method == "POST":
        user = User.objects.get(id=user_id)
        user.is_active = True
        AdminLog.objects.create(
            user=request.user,
            system_name='core',
            action='UPDATE',
            target_model='User',
            target_id=target_user.id,
            description=f"Activated user '{user.username}'"
        )
        user.save()
    return redirect("core:user_list")


@login_required
def save_addresses(request):
    if request.method != "POST":
        return redirect("projectmanagement:pm-settings")

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
        AdminLog.objects.create(
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

        AdminLog.objects.create(
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
            AdminLog.objects.create(
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

            AdminLog.objects.create(
                user=user,
                system_name='core',
                action='UPDATE',
                target_model='Address',
                target_id=billing_address.id,
                description=f"Updated billing address for user '{user.username}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )

    return redirect("projectmanagement:pm-settings")

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    # Never allow deleting home address
    if address.type == 'home':
        return redirect('projectmanagement:pm-settings')

    if request.method == "POST":
        address.delete()

        AdminLog.objects.create(
            user=user,
            system_name='core',
            action='DELETE',
            target_model='Address',
            target_id=address.id,
            description=f"Deleted address for user '{user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    return redirect('projectmanagement:pm-settings')


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

        AdminLog.objects.create(
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
    return redirect('projectmanagement:pm-settings') 


@login_required
@require_POST
def remove_avatar(request):
    if request.user.avatar:
        request.user.avatar.delete(save=False)
        request.user.avatar = None
        request.user.save()
    
        AdminLog.objects.create(
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
    return redirect('projectmanagement:pm-settings') 

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

    AdminLog.objects.create(
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
    return redirect("projectmanagement:pm-settings")

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
            return redirect("projectmanagement:pm-settings")  # redirect to your profile page

        # Check new passwords match
        if new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return redirect("projectmanagement:pm-settings")

        # Optional: validate password strength
        if len(new_password1) < 8:
            messages.error(request, "New password must be at least 8 characters long.")
            return redirect("projectmanagement:pm-settings")

        # Set new password
        user.set_password(new_password1)
        user.save()

        # Keep user logged in after password change
        update_session_auth_hash(request, user)

        messages.success(request, "Password changed successfully.")
        return redirect("projectmanagement:pm-settings")

    # fallback for GET requests
    return redirect("projectmanagement:pm-settings")