from django.urls import path
from . import views

app_name = "performanceevaluation"

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/system-logs/', views.system_logs, name='system_logs'),
    path('admin/manage-user-access/<uuid:user_id>/', views.manage_user_access, name='manage_user_access'),
    path('admin/update-tos/', views.update_tos, name='update_tos'),
    path('admin/criteria/', views.criteria_rubrics, name='criteria_rubrics'),
    path('admin/criteria/add/', views.add_criteria, name='add_criteria'),
    path('admin/criteria/<int:criteria_id>/', views.edit_criteria, name='edit_criteria'),
    path('admin/criteria/<int:criteria_id>/delete/', views.delete_criteria, name='delete_criteria'),
    
    # Academic Setup Routes
    path('admin/academic-setup/', views.academic_setup, name='academic_setup'),
    
    # Academic Terms
    path('admin/academic-term/add/', views.add_academic_term, name='add_academic_term'),
    path('admin/academic-term/<int:term_id>/', views.edit_academic_term, name='edit_academic_term'),
    path('admin/academic-term/<int:term_id>/delete/', views.delete_academic_term, name='delete_academic_term'),
    
    # Evaluation Cycles
    path('admin/evaluation-cycle/add/', views.add_evaluation_cycle, name='add_evaluation_cycle'),
    path('admin/evaluation-cycle/<int:cycle_id>/', views.edit_evaluation_cycle, name='edit_evaluation_cycle'),
    path('admin/evaluation-cycle/<int:cycle_id>/delete/', views.delete_evaluation_cycle, name='delete_evaluation_cycle'),
    
    # Departments
    path('admin/department/add/', views.add_department, name='add_department'),
    path('admin/department/<int:dept_id>/', views.edit_department, name='edit_department'),
    path('admin/department/<int:dept_id>/delete/', views.delete_department, name='delete_department'),
    
    # Evaluation Categories
    path('admin/eval-category/add/', views.add_eval_category, name='add_eval_category'),
]
