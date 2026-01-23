from django.urls import path
from django.shortcuts import redirect
from .views import (
    dashboard,settings,admin_dashboard,deactivate_user,activate_user,delete_user,
    manage_user_access,update_tos, system_logs,save_addresses, delete_address,
    upload_avatar,remove_avatar,profile_update,change_password,
)

app_name = "projectmanagement"

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('projectmanagement:pm_dashboard')
    else:
        return redirect('/projectmanagement/login')

urlpatterns = [
    path('',  root_redirect, name='pm_root'),
    path('dashboard/', dashboard, name='pm_dashboard'),
    path('settings/', settings, name='pm_settings'),

    path('save-addresses/', save_addresses, name='save_addresses'),
    path('address/delete/<uuid:address_id>/', delete_address, name='delete_address'),
    path("avatar/upload/", upload_avatar, name="upload_avatar"),
    path("avatar/remove/", remove_avatar, name="remove_avatar"),
    path("profile/update/", profile_update, name="profile_update"),
    path('change-password/', change_password, name='change_password'),

    # admin routes
    path('admin/dashboard/', admin_dashboard, name='pm_admin_dashboard'),
    path('admin/<uuid:user_id>/deactivate/', deactivate_user, name='deactivate_user'),
    path('admin/<uuid:user_id>/activate/', activate_user, name='activate_user'),
    path('admin/<uuid:user_id>/delete/', delete_user, name='delete_user'),
    path('admin/<uuid:user_id>/manage_access/', manage_user_access, name='manage_user_access'),
    path('admin/update_tos/', update_tos, name='update_tos'),
    path('admin/system_logs/', system_logs, name='pm_system_logs'),
]
