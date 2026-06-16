from django.shortcuts import redirect
from django.urls import path
from . import views

app_name = "informationmanagement"


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("informationmanagement:information-dashboard")
    else:
        return redirect("/informationmanagement/login")


urlpatterns = [
    path("", root_redirect, name="root-redirect"),
    path("admin/dashboard/", views.dashboard, name="information-admin-dashboard"),
    path("dashboard/", views.dashboard, name="information-dashboard"),
    path(
        "dashboard/train-naive-bayes/",
        views.train_naive_bayes_model,
        name="information-train-naive-bayes",
    ),
    path("projects/", views.projects, name="information-projects"),
    path("projects/new/", views.project_create, name="information-project-create"),
    path(
        "projects/<int:pk>/edit/", views.project_edit, name="information-project-edit"
    ),
    path(
        "projects/<int:pk>/delete/",
        views.project_delete,
        name="information-project-delete",
    ),
    path("beneficiaries/", views.beneficiaries, name="information-beneficiaries"),
    path(
        "beneficiaries/new/",
        views.beneficiary_create,
        name="information-beneficiary-create",
    ),
    path(
        "beneficiaries/<int:pk>/edit/",
        views.beneficiary_edit,
        name="information-beneficiary-edit",
    ),
    path(
        "beneficiaries/<int:pk>/delete/",
        views.beneficiary_delete,
        name="information-beneficiary-delete",
    ),
    path("partners/", views.partners, name="information-partners"),
    path("partners/new/", views.partner_create, name="information-partner-create"),
    path(
        "partners/<int:pk>/edit/", views.partner_edit, name="information-partner-edit"
    ),
    path(
        "partners/<int:pk>/delete/",
        views.partner_delete,
        name="information-partner-delete",
    ),
    path("activities/", views.activities, name="information-activities"),
    path("activities/new/", views.activity_create, name="information-activity-create"),
    path(
        "activities/<int:pk>/edit/",
        views.activity_edit,
        name="information-activity-edit",
    ),
    path(
        "activities/<int:pk>/delete/",
        views.activity_delete,
        name="information-activity-delete",
    ),
    path("analytics/", views.analytics, name="information-analytics"),
    path("reports/", views.reports, name="information-reports"),
    path("reports/new/", views.report_create, name="information-report-create"),
    path("reports/<int:pk>/edit/", views.report_edit, name="information-report-edit"),
    path(
        "reports/<int:pk>/delete/",
        views.report_delete,
        name="information-report-delete",
    ),
    path(
        "reports/templates/new/",
        views.report_template_create,
        name="information-report-template-create",
    ),
    path("ml-lab/", views.ml_lab, name="information-ml-lab"),
    path(
        "ml-lab/models/new/", views.ml_model_create, name="information-ml-model-create"
    ),
    path(
        "ml-lab/models/<int:pk>/edit/",
        views.ml_model_edit,
        name="information-ml-model-edit",
    ),
    path(
        "ml-lab/models/<int:pk>/delete/",
        views.ml_model_delete,
        name="information-ml-model-delete",
    ),
    path(
        "ml-lab/pipelines/new/",
        views.ml_pipeline_create,
        name="information-ml-pipeline-create",
    ),
    path(
        "ml-lab/pipelines/<int:pk>/edit/",
        views.ml_pipeline_edit,
        name="information-ml-pipeline-edit",
    ),
    path(
        "ml-lab/pipelines/<int:pk>/delete/",
        views.ml_pipeline_delete,
        name="information-ml-pipeline-delete",
    ),
    path(
        "ml-lab/experiments/new/",
        views.ml_experiment_create,
        name="information-ml-experiment-create",
    ),
    path(
        "ml-lab/experiments/<int:pk>/edit/",
        views.ml_experiment_edit,
        name="information-ml-experiment-edit",
    ),
    path(
        "ml-lab/experiments/<int:pk>/delete/",
        views.ml_experiment_delete,
        name="information-ml-experiment-delete",
    ),
    
    # ========================================================================
    # Feature 1: Contribution Allocation Management URLs
    # ========================================================================
    path("funds/", views.contribution_funds_list, name="contribution-funds-list"),
    path("funds/new/", views.contribution_fund_create, name="contribution-fund-create"),
    path("funds/<int:pk>/", views.contribution_fund_detail, name="contribution-fund-detail"),
    path("allocations/new/", views.fund_allocation_create, name="fund-allocation-create"),
    path("expenses/new/", views.fund_expense_create, name="fund-expense-create"),
    
    # ========================================================================
    # Feature 2: Financial Reporting URLs
    # ========================================================================
    path("financial/dashboard/", views.financial_dashboard, name="financial-dashboard"),
    path("reports/financial-summary/", views.financial_summary_report, name="financial-summary-report"),
    path("reports/fund-utilization/", views.fund_utilization_report, name="fund-utilization-report"),
    path("reports/monthly-contribution/", views.monthly_contribution_report, name="monthly-contribution-report"),
    path("reports/annual-financial/", views.annual_financial_report, name="annual-financial-report"),
    path("reports/export/<str:report_type>/", views.export_financial_report, name="export-financial-report"),
    
    # ========================================================================
    # Feature 3: Member Contribution Monitoring URLs
    # ========================================================================
    path("members/contributions/", views.member_contributions_list, name="member-contributions-list"),
    path("members/contributions/<int:pk>/", views.member_contribution_detail, name="member-contribution-detail"),
    path("members/contributions/new/", views.member_contribution_create, name="member-contribution-create"),
    path("members/contributions/<int:pk>/edit/", views.member_contribution_edit, name="member-contribution-edit"),
    path("members/contributions/<int:pk>/export/", views.export_member_statement, name="export-member-statement"),
    
    # Master Data - Departments
    path("master-data/departments/", views.master_data_departments_list, name="master-data-departments-list"),
    path("master-data/departments/new/", views.master_data_department_create, name="master-data-department-create"),
    path("master-data/departments/<int:pk>/edit/", views.master_data_department_edit, name="master-data-department-edit"),
]
