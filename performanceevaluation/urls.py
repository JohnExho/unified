from django.urls import path
from . import views

app_name = "performanceevaluation"

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/system-logs/', views.system_logs, name='system_logs'),
    path('admin/manage-user-access/<uuid:user_id>/', views.manage_user_access, name='manage_user_access'),
    path('admin/update-tos/', views.update_tos, name='update_tos'),
]
