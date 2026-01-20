from django.urls import path
from django.shortcuts import redirect
from .views import (
    core_login, core_logout, system_selection,
    core_register, manage_user_systems, user_list,
    deactivate_user, activate_user, save_addresses,
    delete_address, upload_avatar, remove_avatar,
    profile_update, change_password, dashboard,
)

app_name = "core"

def core_root(request):
    if request.user.is_authenticated:
        return redirect('core:core_dashboard')
    return redirect('core:core_login')

urlpatterns = [
    # Auth - Generic login (no system specified)
    path('login/', core_login, name='core_login'),
    path('', core_root, name='core_login_root'),  # Root redirect
    
    # Auth - System-specific
    path('<str:system_name>/login/', core_login, name='core_system_login'),
    path('<str:system_name>/register/', core_register, name='core_register'),
    path('logout/', core_logout, name='core_logout'),  # generic logout
    path('<str:system_name>/logout/', core_logout, name='core_system_logout'),  # system logout
    # User flow
    path('dashboard/', dashboard, name='core_dashboard'),
    path('select-system/', system_selection, name='system_selection'),
    path('save-addresses/', save_addresses, name='save_addresses'),
    path('address/delete/<uuid:address_id>/', delete_address, name='delete_address'),
    path("avatar/upload/", upload_avatar, name="upload_avatar"),
    path("avatar/remove/", remove_avatar, name="remove_avatar"),
    path("profile/update/", profile_update, name="profile_update"),
    path('change-password/', change_password, name='change_password'),

    # Admin control plane
    path('users/', user_list, name='user_list'),
    
    # User group management
    path('users/<uuid:user_id>/access/',
        manage_user_systems,
        name='manage_user_systems'
    ),

    # User activation/deactivation
    path("users/<uuid:user_id>/deactivate/", deactivate_user, name="deactivate_user"),
    path("users/<uuid:user_id>/activate/", activate_user, name="activate_user"),
]