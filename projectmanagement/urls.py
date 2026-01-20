from django.urls import path
from django.shortcuts import redirect
from .views import (
    dashboard,
    settings,
    admin_dashboard,
)

app_name = "projectmanagement"

def root_redirect(request):
    return redirect('projectmanagement:pm-dashboard')

urlpatterns = [
    path('',  root_redirect, name='pm-root'),
    path('dashboard/', dashboard, name='pm-dashboard'),
    path('settings/', settings, name='pm-settings'),

    # admin routes
    path('admin/dashboard/', admin_dashboard, name='pm-admin-dashboard'),
]
