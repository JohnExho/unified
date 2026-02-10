from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import get_user_model, update_session_auth_hash
from .models import CustomUser, Logs, Address, Systems, SystemMembership
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

    # Fetch the system and its terms of service
    # Note: 'name' is the field in Systems table, not 'system_name'
    try:
        system = Systems.objects.get(name=system_name)
        system_info = {
            "name": system.name,
            "description": system.description,
            "terms_of_service": system.terms_of_service,
            "display_name": (
                system.display_name
                if hasattr(system, "display_name")
                else system.name.title()
            ),
        }
    except Systems.DoesNotExist:
        system_info = {
            "name": system_name,
            "description": None,
            "terms_of_service": None,
            "display_name": system_name.title(),
        }
        messages.warning(request, f"System '{system_name}' not found in database.")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        first_name = request.POST.get("first_name")
        middle_name = request.POST.get("middle_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        terms_accepted = request.POST.get("terms_accepted")
        avatar = request.FILES.get("avatar")
        avatar_url = request.POST.get("avatar_url")

        # Validate terms
        if terms_accepted != "true":
            messages.error(
                request, "You must accept the Terms and Conditions to register."
            )
            return render(
                request,
                "core/pages/register.html",
                {
                    "error": "Accept the Terms and Conditions",
                    "system_name": system_name,
                    "system_info": system_info,
                },
            )

        if not username or not password:
            messages.error(request, "Please fill in all required fields.")
            return render(
                request,
                "core/pages/register.html",
                {
                    "error": "Fill all required fields",
                    "system_name": system_name,
                    "system_info": system_info,
                },
            )

        if password and len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(
                request,
                "core/pages/register.html",
                {
                    "error": "Password too short",
                    "system_name": system_name,
                    "system_info": system_info,
                },
            )

        # Check password confirmation
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(
                request,
                "core/pages/register.html",
                {
                    "error": "Passwords do not match",
                    "system_name": system_name,
                    "system_info": system_info,
                },
            )

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(
                request,
                "core/pages/register.html",
                {
                    "error": "Username already exists",
                    "system_name": system_name,
                    "system_info": system_info,
                },
            )

        # Create the user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            avatar_url=avatar_url,
        )

        if avatar:
            user.avatar = avatar
            user.save()

        # Log registration
        Logs.objects.create(
            user=user,
            system_name=system_name,
            action="REGISTER",
            target_model="User",
            target_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            description=f"User '{username}' registered.",
            hidden_description=f"User '{username}' registered for {system_name}",
        )

        # Assign system membership
        SystemMembership.objects.create(
            user=user, system_name=system_name, system_role="user"
        )

        messages.success(request, "Registration successful. Please log in.")

        # Redirect to system-specific login
        if system_name != "core":
            messages.info(request, f"You can now log in.")
            return redirect(f"/{system_name}/login/")
        return redirect("core:core_login")

    # GET request: render form with terms
    return render(
        request,
        "core/pages/register.html",
        {"system_name": system_name, "system_info": system_info},
    )


def core_login(request, system_name=None):
    User = get_user_model()
    form = LoginForm(request.POST or None)

    # Fetch system info if system_name is provided
    system_info = None
    if system_name:
        try:
            system = Systems.objects.get(name=system_name)
            system_info = {
                "name": system.name,
                "description": system.description,
                "display_name": (
                    system.display_name
                    if hasattr(system, "display_name")
                    else system.description or system.name.title()
                ),
            }
        except Systems.DoesNotExist:
            system_info = {
                "name": system_name,
                "description": None,
                "display_name": system_name.title(),
            }

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        user = authenticate(request, username=username, password=password)

        if not user:
            form.add_error(None, "Invalid username or password.")
            return render(
                request,
                "core/pages/login.html",
                {"form": form, "system_name": system_name, "system_info": system_info},
            )

        # Superuser-only check for /login
        if not system_name and not user.is_superuser:
            messages.error(request, "Oopps! You do not have access to the core system.")
            return redirect("core:core_login")

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
        if system_name and any(s["url"] == system_name for s in accessible_systems):
            target_system = next(
                s for s in accessible_systems if s["url"] == system_name
            )
            request.session["current_system"] = target_system["url"]
            Logs.objects.create(
                user=user,
                target_model="User",
                system_name=system_name,
                target_id=user.id,
                action="LOGIN",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                description=f"User logged in.",
                hidden_description=f"User logged in for {system_name}",
            )
            messages.success(request, f"Welcome {user.username}!")
            return redirect(get_dashboard_url(target_system))

        # 2. User has only one system
        elif len(accessible_systems) == 1:
            target_system = accessible_systems[0]
            request.session["current_system"] = target_system["url"]
            Logs.objects.create(
                user=user,
                target_model="User",
                system_name=target_system["url"],
                target_id=user.id,
                action="LOGIN",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                description=f"User logged in.",
                hidden_description=f"User logged in for {target_system['url']}",
            )
            return redirect(get_dashboard_url(target_system))

        # 3. Multiple systems, let them choose
        elif len(accessible_systems) > 1:
            request.session["accessible_systems"] = accessible_systems
            messages.info(request, "Please select a system to continue.")
            return redirect("core:system_selection")

        else:
            messages.error(request, "You are not assigned to any system.")
            return redirect("core:core_login")

    return render(
        request,
        "core/pages/login.html",
        {"form": form, "system_name": system_name, "system_info": system_info},
    )


def system_selection(request):
    systems = request.session.get("accessible_systems")

    if not systems and not request.user.is_superuser:
        messages.error(request, "No Access.")
        return redirect("core:core_login")

    # --- Ensure 'core' is always first ---
    systems = sorted(systems, key=lambda s: 0 if s.get("url") == "core" else 1)

    # Persist the ordered list (important for POST validation consistency)
    request.session["accessible_systems"] = systems

    if request.method == "POST":
        selected_system = request.POST.get("system")

        # Verify the user has access to this system
        if any(s["url"] == selected_system for s in systems):
            Logs.objects.create(
                user=request.user,
                target_model="User",
                system_name=selected_system,
                target_id=request.user.id,
                action="LOGIN",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                description=f"User logged in.",
                hidden_description=f"User logged in for {selected_system}",
            )

            # Clear selection list after use
            del request.session["accessible_systems"]
            request.session["current_system"] = selected_system

            if selected_system == "core":
                return redirect("core:core_dashboard")
            return redirect(f"/{selected_system}")

        messages.error(request, "Invalid system selection.")
        return redirect("core:core_login")

    return render(request, "core/pages/system_selection.html", {"systems": systems})


def core_logout(request, system_name=None):
    # Resolve current system
    current_system = system_name or request.session.get("current_system", "core")

    # Capture user state BEFORE logout
    is_admin = request.user.is_authenticated and request.user.is_superuser

    # Log logout action
    if request.user.is_authenticated:
        Logs.objects.create(
            user=request.user,
            target_model="User",
            system_name=current_system,
            target_id=request.user.id,
            action="LOGOUT",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            description=f"User logged out.",
            hidden_description=f"User logged out from {current_system}",
        )

    # Logout and clear session
    auth_logout(request)
    request.session.flush()

    messages.info(request, "You have been logged out.")

    # Admins ALWAYS go to core
    if is_admin:
        return redirect("core:core_login")

    # Non-core systems redirect to their own login
    if current_system != "core":
        return redirect(f"/{current_system}/login/")

    return redirect("core:core_login")


def not_found_page(request):
    return render(request, "404.html", status=404)


def dashboard(request):
    # Get accessible systems from db with their actual names
    systems = Systems.objects.values(
        "name", "description"
    )  # or 'label' if you have that
    logs = Logs.objects.all().order_by("-created_at")[:10]  # recent 10 logs

    # Get all users except the current user
    users_qs = User.objects.exclude(id=request.user.id).order_by("-date_joined")

    paginator = Paginator(users_qs, 10)
    page_number = request.GET.get("page")
    users = paginator.get_page(page_number)

    return render(
        request,
        "core/pages/dashboard.html",
        {
            "users": users,
            "total_users": users_qs.count(),
            "systems": systems,
            "logs": logs,
        },
    )


@user_passes_test(lambda u: u.is_superuser)
def manage_user_systems(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    if request.user == target_user:
        return render(request, "404.html", status=404)

    all_systems = Systems.objects.values("name", "description")

    if request.method == "POST":
        action = request.POST.get("action")

        old_memberships = {
            m.system_name: m for m in target_user.systemmembership_set.all()
        }
        old_systems = set(old_memberships.keys())

        # CLEAR ALL FEATURE
        if action == "clear":
            target_user.systemmembership_set.all().delete()

            for system_name in old_systems:
                Logs.objects.create(
                    user=request.user,
                    system_name="core",
                    action="UPDATE",
                    target_model="User",
                    target_id=target_user.id,
                    description=f"Cleared user '{target_user.username}' from system '{system_name}'",
                    hidden_description=f"Cleared user '{target_user.username}' from system '{system_name}'",
                )

            return redirect("core:manage_user_systems", user_id=user_id)

        # NORMAL SAVE FLOW
        selected_systems = set(request.POST.getlist("systems"))

        # REMOVE systems
        for system_name in old_systems - selected_systems:
            old_memberships[system_name].delete()
            Logs.objects.create(
                user=request.user,
                system_name="core",
                action="UPDATE",
                target_model="User",
                target_id=target_user.id,
                description=f"Removed user '{target_user.username}' from system '{system_name}'",
                hidden_description=f"Removed user '{target_user.username}' from system '{system_name}'",
            )

        # ADD or UPDATE systems + roles
        for system_name in selected_systems:
            role = request.POST.get(f"role_{system_name}", "admin")

            if system_name in old_memberships:
                membership = old_memberships[system_name]

                if membership.system_role != role:
                    membership.system_role = role
                    membership.save(update_fields=["system_role"])

                    Logs.objects.create(
                        user=request.user,
                        system_name="core",
                        action="UPDATE",
                        target_model="User",
                        target_id=target_user.id,
                        description=(
                            f"Updated role for user '{target_user.username}' "
                            f"in system '{system_name}' to '{role}'"
                        ),
                        hidden_description=(
                            f"Updated role for user '{target_user.username}' "
                            f"in system '{system_name}' to '{role}'"
                        ),
                    )
            else:
                SystemMembership.objects.create(
                    user=target_user, system_name=system_name, system_role="admin"
                )

                Logs.objects.create(
                    user=request.user,
                    system_name="core",
                    action="UPDATE",
                    target_model="User",
                    target_id=target_user.id,
                    description=(
                        f"Added user '{target_user.username}' "
                        f"to system '{system_name}' with role '{role}'"
                    ),
                    hidden_description=(
                        f"Added user '{target_user.username}' "
                        f"to system '{system_name}' with role '{role}'"
                    ),
                )

        return redirect("core:core_dashboard")

    # GET
    user_systems = target_user.systemmembership_set.values_list(
        "system_name", flat=True
    )

    system_roles = {
        m.system_name: m.system_role for m in target_user.systemmembership_set.all()
    }

    return render(
        request,
        "core/pages/manage_user_systems.html",
        {
            "target_user": target_user,
            "all_systems": all_systems,
            "user_systems": user_systems,
            "system_roles": system_roles,
        },
    )


@require_http_methods(["POST"])
def deactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()

    Logs.objects.create(
        user=request.user,
        system_name="core",
        action="UPDATE",
        target_model="User",
        target_id=user.id,  # Fixed: was target_user.id
        description=f"Deactivated user '{user.username}'",
        hidden_description=f"Deactivated user '{user.username}'",
    )

    return redirect("core:core_dashboard")  # Changed to redirect to dashboard


@require_http_methods(["POST"])
def activate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()

    Logs.objects.create(
        user=request.user,
        system_name="core",
        action="UPDATE",
        target_model="User",
        target_id=user.id,  # Fixed: was target_user.id
        description=f"Activated user '{user.username}'",
        hidden_description=f"Activated user '{user.username}'",
    )

    return redirect("core:core_dashboard")  # Changed to redirect to dashboard


def core_delete_user(request, user_id):
    """
    Delete a user by their ID.
    Only accessible by superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect("core:core_dashboard")

    target_user = get_object_or_404(User, id=user_id)

    if request.user == target_user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("core:core_dashboard")

    if request.method == "POST":
        username = target_user.username
        target_user.delete()

        Logs.objects.create(
            user=request.user,
            system_name="core",
            action="DELETE",
            target_model="User",
            target_id=user_id,
            description=f"Deleted user '{username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            hidden_description=f"Deleted user '{username}'",
        )

        Logs.objects.create(
            user=request.user,
            system_name="core",
            action="DELETE",
            target_model="SystemMembership",
            target_id=None,
            description=f"Deleted all system memberships for user '{username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            hidden_description=f"Deleted all system memberships for user '{username}'",
        )

        messages.success(request, f"User '{username}' has been deleted.")
        return redirect("core:core_dashboard")

    # If not POST, redirect to dashboard
    return redirect("core:core_dashboard")


@user_passes_test(lambda u: u.is_superuser)
def create_system_admin(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")
        system_access = request.POST.getlist("system_access")

        # Validation
        if not username or not email or not password1:
            messages.error(request, "Please fill in all required fields.")
            return redirect("core:core_dashboard")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("core:core_dashboard")

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect("core:core_dashboard")

        if not system_access:
            messages.error(request, "Please select at least one system for the admin.")
            return redirect("core:core_dashboard")

        # Friendly pre-checks (UX)
        if User.objects.filter(username=username).exists():
            messages.info(request, f"Username '{username}' already exists.")
            return redirect("core:core_dashboard")

        # Email uniqueness check (email stored as plaintext)
        if User.objects.filter(email=email).exists():
            messages.info(request, f"Email '{email}' is already registered.")
            return redirect("core:core_dashboard")

        try:
            admin_user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                is_staff=True,
                is_active=True,
            )

            Logs.objects.create(
                user=request.user,
                system_name="core",
                action="CREATE",
                target_model="User",
                target_id=admin_user.id,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                description=f"Created superadmin user '{username}'",
                hidden_description=f"Created superadmin user '{username}'",
            )

            for system_name in system_access:
                membership = SystemMembership.objects.create(
                    user=admin_user,
                    system_name=system_name.lower(),
                    system_role="superadmin",
                )

                Logs.objects.create(
                    user=request.user,
                    system_name="core",
                    action="CREATE",
                    target_model="SystemMembership",
                    target_id=membership.id,
                    ip_address=get_client_ip(request),
                    user_agent=get_user_agent(request),
                    description=(
                        f"Assigned superadmin '{username}' "
                        f"to system '{system_name}' with superadmin role"
                    ),
                    hidden_description=(
                        f"Assigned superadmin '{username}' "
                        f"to system '{system_name}' with superadmin role"
                    ),
                )

            messages.success(
                request, f"Super Admin user '{username}' created successfully."
            )
            return redirect("core:core_dashboard")

        except IntegrityError:
            # Race-condition safe fallback
            messages.info(request, "A user with this username or email already exists.")
            return redirect("core:core_dashboard")

        except Exception:
            # True unexpected failure
            messages.error(
                request, "An unexpected error occurred while creating the admin user."
            )
            return redirect("core:core_dashboard")

    return redirect("core:core_dashboard")
