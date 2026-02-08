from django.urls import path
from . import views

app_name = "performanceevaluation"

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('evaluations/', views.user_evaluations, name='user_evaluations'),
    path('evaluations/form/<int:form_id>/', views.user_evaluation_form, name='user_evaluation_form'),
    path('results-analytics/', views.user_results_analytics, name='user_results_analytics'),
    path('results-analytics/<int:evaluation_id>/', views.user_evaluation_review, name='user_evaluation_review'),
    path('settings/', views.settings, name='settings'),
    path('settings/upload-avatar/', views.upload_avatar, name='upload_avatar'),
    path('settings/remove-avatar/', views.remove_avatar, name='remove_avatar'),
    path('settings/profile-update/', views.profile_update, name='profile_update'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/save-addresses/', views.save_addresses, name='save_addresses'),
    path('settings/delete-address/<uuid:address_id>/', views.delete_address, name='delete_address'),
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

    # Evaluation Activity
    path('admin/evaluation-activity/', views.evaluation_activity, name='evaluation_activity'),
    path('admin/evaluations/add/', views.add_evaluation, name='add_evaluation'),
    path('admin/evaluations/<int:evaluation_id>/', views.edit_evaluation, name='edit_evaluation'),
    path('admin/evaluations/<int:evaluation_id>/delete/', views.delete_evaluation, name='delete_evaluation'),
    path('admin/evaluation-scores/add/', views.add_evaluation_score, name='add_evaluation_score'),
    path('admin/evaluation-scores/<int:score_id>/', views.edit_evaluation_score, name='edit_evaluation_score'),
    path('admin/evaluation-scores/<int:score_id>/delete/', views.delete_evaluation_score, name='delete_evaluation_score'),
    path('admin/evaluation-comments/add/', views.add_evaluation_comment, name='add_evaluation_comment'),
    path('admin/evaluation-comments/<int:comment_id>/', views.edit_evaluation_comment, name='edit_evaluation_comment'),
    path('admin/evaluation-comments/<int:comment_id>/delete/', views.delete_evaluation_comment, name='delete_evaluation_comment'),

    # Results & Analytics
    path('admin/results-analytics/', views.results_analytics, name='results_analytics'),
    path('admin/results-analytics/compute/', views.compute_results, name='compute_results'),
    path('admin/results-analytics/<int:result_id>/recommendations/', views.results_analytics_recommendations, name='results_analytics_recommendations'),

    # Evaluation Structure
    path('admin/evaluation-structure/', views.evaluation_structure, name='evaluation_structure'),
    path('admin/evaluation-forms/add/', views.add_evaluation_form, name='add_evaluation_form'),
    path('admin/evaluation-forms/<int:form_id>/', views.edit_evaluation_form, name='edit_evaluation_form'),
    path('admin/evaluation-forms/<int:form_id>/delete/', views.delete_evaluation_form, name='delete_evaluation_form'),
    path('admin/evaluation-categories/add/', views.add_evaluation_category, name='add_evaluation_category'),
    path('admin/evaluation-categories/<int:category_id>/', views.edit_evaluation_category, name='edit_evaluation_category'),
    path('admin/evaluation-categories/<int:category_id>/delete/', views.delete_evaluation_category, name='delete_evaluation_category'),
    path('admin/evaluation-criteria/add/', views.add_evaluation_criteria, name='add_evaluation_criteria'),
    path('admin/evaluation-criteria/<int:criteria_id>/', views.edit_evaluation_criteria, name='edit_evaluation_criteria'),
    path('admin/evaluation-criteria/<int:criteria_id>/delete/', views.delete_evaluation_criteria, name='delete_evaluation_criteria'),
    path('admin/rubrics/add/', views.add_rubric, name='add_rubric'),
    path('admin/rubrics/<int:rubric_id>/', views.edit_rubric, name='edit_rubric'),
    path('admin/rubrics/<int:rubric_id>/delete/', views.delete_rubric, name='delete_rubric'),
]
