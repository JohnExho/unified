from django.urls import path
from django.shortcuts import redirect
from .views import (
    dashboard,
    settings,
    admin_dashboard,
    deactivate_user,
    activate_user,
    delete_user,
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

    # admin routes
    path('admin/dashboard/', admin_dashboard, name='pm_admin_dashboard'),
    path('admin/<uuid:user_id>/deactivate/', deactivate_user, name='deactivate_user'),
    path('admin/<uuid:user_id>/activate/', activate_user, name='activate_user'),
    path('admin/<uuid:user_id>/delete/', delete_user, name='delete_user'),
]
