from django.urls import path
from django.shortcuts import redirect
from . import views
from .views import (
    dashboard,settings,admin_dashboard,deactivate_user,activate_user,delete_user,
    manage_user_access,update_tos, system_logs,save_addresses, delete_address,
    upload_avatar,remove_avatar,profile_update,change_password,projects,create_project,
    create_task, teams, add_team, delete_team, add_team_user, remove_team_user,
    calendar, reports,
    # notifications,
    complete_task, assign_task, edit_project,
    edit_task, delete_task, delete_project
)

app_name = "projectmanagement"

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('projectmanagement:pm_dashboard')
    else:
        return redirect('/researchmanagement/login')

urlpatterns = [
    path('',  root_redirect, name='pm_root'),
    path('dashboard/', dashboard, name='pm_dashboard'),
    path('projects/', projects, name='pm_projects'),
    path('projects/create/', create_project, name='create_project'),
    path('projects/<uuid:project_id>/tasks/create/', create_task, name='create_task'),
    path('projects/<uuid:project_id>/edit/', edit_project, name='edit_project'),
    path('projects/<uuid:project_id>/delete/', delete_project, name='delete_project'),
    path('tasks/<uuid:task_id>/edit/', edit_task, name='edit_task'),
    path('tasks/<uuid:task_id>/delete/', delete_task, name='delete_task'),
    path('tasks/<uuid:task_id>/complete/', complete_task, name='complete_task'),
    path('tasks/<uuid:task_id>/assign/', assign_task, name='assign_task'),
    path('teams/', teams, name='pm_teams'),
    path('teams/add/', add_team, name='add_team'),
    path('teams/<uuid:team_id>/delete/', delete_team, name='delete_team'),
    path('teams/<uuid:team_id>/add-user/', add_team_user, name='add_team_user'),
    path('teams/<uuid:team_id>/remove-user/<uuid:user_id>/', remove_team_user, name='remove_team_user'),
    path('calendar/', calendar, name='pm_calendar'),
    path('reports/', reports, name='pm_reports'),
    # path('notifications/', notifications, name='pm_notifications'),
    path('settings/', settings, name='pm_settings'),

    # API endpoints for task assignment
    path('api/users/', views.api_users, name='api_users'),
    path('api/teams/', views.api_teams, name='api_teams'),
    path('api/tasks/<uuid:task_id>/assignees/', views.api_task_assignees, name='api_task_assignees'),

    path('save-addresses/', save_addresses, name='save_addresses'),
    path('address/delete/<uuid:address_id>/', delete_address, name='delete_address'),
    path("avatar/upload/", upload_avatar, name="upload_avatar"),
    path("avatar/remove/", remove_avatar, name="remove_avatar"),
    path("profile/update/", profile_update, name="profile_update"),
    path('change-password/', change_password, name='change_password'),

    # admin routes
    path('admin/dashboard/', admin_dashboard, name='pm_admin_dashboard'),
    path('admin/deactivate//<uuid:user_id>', deactivate_user, name='deactivate_user'),
    path('admin/<uuid:user_id>/activate/', activate_user, name='activate_user'),
    path('admin/<uuid:user_id>/delete/', delete_user, name='delete_user'),
    path('admin/<uuid:user_id>/manage_access/', manage_user_access, name='manage_user_access'),
    path('admin/update_tos/', update_tos, name='update_tos'),
    path('admin/system_logs/', system_logs, name='pm_system_logs'),
    path('admin/ml-lab/', views.ml_lab, name='ml_lab'),
]
