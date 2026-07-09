from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = "scholarshipmanagement"


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('scholarshipmanagement:sm_dashboard')
    return redirect('/scholarshipmanagement/login')


urlpatterns = [
    path('', root_redirect, name='sm_root'),

    # Dashboard
    path('dashboard/', views.dashboard, name='sm_dashboard'),

    # Profile Setup (Stage 1)
    path('profile/', views.profile_setup, name='profile_setup'),
    path('profile/document/upload/', views.upload_document, name='upload_document'),
    path('profile/document/<uuid:doc_id>/delete/', views.delete_document, name='delete_document'),

    # Scholarships (Stage 2 – Browse)
    path('scholarships/', views.scholarships, name='sm_scholarships'),
    path('scholarships/<uuid:scholarship_id>/', views.scholarship_detail, name='scholarship_detail'),
    path('scholarships/<uuid:scholarship_id>/apply/', views.apply_scholarship, name='apply_scholarship'),

    # My Applications (Student)
    path('applications/', views.my_applications, name='my_applications'),
    path('applications/<uuid:application_id>/', views.application_detail, name='application_detail'),
    path('applications/<uuid:application_id>/offer/respond/', views.respond_offer, name='respond_offer'),

    # Staff / Reviewer
    path('staff/applications/', views.staff_applications, name='staff_applications'),
    path('staff/applications/<uuid:application_id>/evaluate/', views.evaluate_application, name='evaluate_application'),

    # Admin: Scholarship Management
    path('admin/scholarships/create/', views.create_scholarship, name='create_scholarship'),
    path('admin/scholarships/<uuid:scholarship_id>/edit/', views.edit_scholarship, name='edit_scholarship'),
    path('admin/scholarships/<uuid:scholarship_id>/delete/', views.delete_scholarship, name='delete_scholarship'),

    # Admin: Application Decisions
    path('admin/applications/', views.admin_applications, name='admin_applications'),
    path('admin/applications/<uuid:application_id>/decide/', views.decide_application, name='decide_application'),

    # Admin: Reports
    path('admin/reports/', views.reports, name='sm_reports'),

    # Admin: User Management
    path('admin/dashboard/', views.admin_dashboard, name='sm_admin_dashboard'),
    path('admin/users/<uuid:user_id>/deactivate/', views.deactivate_user, name='deactivate_user'),
    path('admin/users/<uuid:user_id>/activate/', views.activate_user, name='activate_user'),
    path('admin/users/<uuid:user_id>/access/', views.manage_user_access, name='manage_user_access'),

    # Admin: System Logs
    path('admin/logs/', views.system_logs, name='system_logs'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),

    # ML Recommendations
    path('recommendations/', views.ml_recommendations, name='ml_recommendations'),
    path('ml-model/', views.ml_model_page, name='ml_model'),
    path('performance/', views.student_performance, name='student_performance'),
    path('admin/monitoring/', views.admin_monitoring, name='admin_monitoring'),

    # Settings
    path('settings/', views.settings, name='sm_settings'),

    # API
    path('api/scholarships/<uuid:scholarship_id>/stats/', views.api_scholarship_stats, name='api_scholarship_stats'),
]
