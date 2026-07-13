from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.text import slugify
from django.contrib import messages
from django.views.decorators.http import require_POST
from core.decorators import require_system_access, require_system_role
from core.services import Services
from .models import (
    Project,
    BeneficiaryGroup,
    Partner,
    Activity,
    Report,
    ReportTemplate,
    MLModel,
    MLPipeline,
    MLExperiment,
    ContributionFund,
    FundAllocation,
    FundExpense,
    MemberContributionRecord,
    MasterDataDepartment,
)
from .forms import (
    ProjectForm,
    BeneficiaryGroupForm,
    PartnerForm,
    ActivityForm,
    ReportForm,
    ReportTemplateForm,
    MLModelForm,
    MLPipelineForm,
    MLExperimentForm,
    ContributionFundForm,
    FundAllocationForm,
    FundExpenseForm,
    MemberContributionRecordForm,
    MemberContributionEntryForm,
    MemberContributionFilterForm,
    MasterDataDepartmentForm,
)
from .forms import (
    ProjectForm,
    BeneficiaryGroupForm,
    PartnerForm,
    ActivityForm,
    ReportForm,
    ReportTemplateForm,
    MLModelForm,
    MLPipelineForm,
    MLExperimentForm,
)
from .services import InformationClassificationService


def _has_information_access(request):
    return request.user.has_perm(
        "informationmanagement.access_information_management_system"
    )


def _base_context(request):
    return {
        "systems": request.session.get("accessible_systems", []),
    }


def _sector_coverage(projects):
    totals = projects.values("category").annotate(count=Count("id")).order_by("-count")
    total_count = sum(item["count"] for item in totals) or 0
    coverage = []
    for item in totals:
        percentage = 0 if total_count == 0 else round(item["count"] / total_count * 100)
        coverage.append(
            {
                "name": item["category"],
                "key": slugify(item["category"], allow_unicode=False),
                "value": percentage,
            }
        )
    return coverage


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def dashboard(request):
    if not Services.has_access(request.user, "informationmanagement"):
        return render(request, "404.html", status=404)

    projects_qs = Project.objects.all()
    partners_count = Partner.objects.count()
    beneficiaries_total = (
        BeneficiaryGroup.objects.aggregate(total=Sum("households"))["total"] or 0
    )
    active_projects = projects_qs.filter(status="Ongoing").count()
    activities_month = Activity.objects.filter(
        date__month=timezone.now().month,
        date__year=timezone.now().year,
    ).count()

    stats = [
        {
            "label": "Active Projects",
            "value": active_projects,
            "trend": "up",
            "delta": 0,
        },
        {"label": "Partner Orgs", "value": partners_count, "trend": "up", "delta": 0},
        {
            "label": "Beneficiaries",
            "value": beneficiaries_total,
            "trend": "up",
            "delta": 0,
        },
        {
            "label": "Activities This Month",
            "value": activities_month,
            "trend": "up",
            "delta": 0,
        },
    ]

    nb_snapshot = InformationClassificationService.get_dashboard_snapshot(limit=5)
    can_train_nb_model = (
        request.user.is_superuser
        or Services.has_access(
            request.user,
            "informationmanagement",
            role="admin",
        )
        or Services.has_access(
            request.user,
            "informationmanagement",
            role="superadmin",
        )
    )

    context = {
        **_base_context(request),
        "stats": stats,
        "projects": projects_qs.order_by("-start_date")[:5],
        "recent_activities": Activity.objects.order_by("-date")[:5],
        "sector_coverage": _sector_coverage(projects_qs),
        "ml_summary": {
            "models": MLModel.objects.count(),
            "pipelines": MLPipeline.objects.count(),
            "experiments": MLExperiment.objects.count(),
        },
        "nb_predictions": nb_snapshot["predictions"],
        "nb_model_ready": nb_snapshot["model_ready"],
        "nb_uses_fallback": nb_snapshot["uses_fallback"],
        "can_train_nb_model": can_train_nb_model,
    }
    return render(request, "informationmanagement/dashboard.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
@require_POST
def train_naive_bayes_model(request):
    """Train IMS Naive Bayes classifier and refresh project predictions."""
    days_raw = request.POST.get("days", "3650")

    try:
        days = int(days_raw)
    except (TypeError, ValueError):
        days = 3650

    if days <= 0:
        days = 3650

    result = InformationClassificationService.train_naive_bayes_classifier(
        lookback_days=days
    )

    if result.get("trained"):
        predictions = InformationClassificationService.predict_project_success()
        accuracy = result.get("accuracy")
        if accuracy is not None:
            messages.success(
                request,
                f"Naive Bayes trained (accuracy: {accuracy}). Updated {len(predictions)} predictions.",
            )
        else:
            messages.success(
                request,
                f"Naive Bayes trained. Updated {len(predictions)} predictions.",
            )
    else:
        messages.warning(
            request,
            f"Training skipped: {result.get('reason', 'insufficient data')}",
        )

    return redirect("informationmanagement:information-dashboard")


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def projects(request):
    if not Services.has_access(request.user, "informationmanagement"):
        return render(request, "404.html", status=404)

    context = {
        **_base_context(request),
        "projects": Project.objects.order_by("-start_date"),
        "filters": [choice[0] for choice in Project.CATEGORY_CHOICES],
    }
    return render(request, "informationmanagement/projects.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def beneficiaries(request):
    if not Services.has_access(request.user, "informationmanagement"):
        return render(request, "404.html", status=404)

    context = {
        **_base_context(request),
        "segments": BeneficiaryGroup.objects.order_by("-priority"),
        "communities": BeneficiaryGroup.objects.order_by("-priority"),
    }
    return render(request, "informationmanagement/beneficiaries.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def partners(request):
    if not Services.has_access(request.user, "informationmanagement"):
        return render(request, "404.html", status=404)

    partners_qs = Partner.objects.order_by("name")
    pipeline = (
        partners_qs.values("status").annotate(count=Count("id")).order_by("status")
    )
    context = {
        **_base_context(request),
        "partners": partners_qs,
        "pipeline": [
            {"stage": item["status"], "count": item["count"]} for item in pipeline
        ],
    }
    return render(request, "informationmanagement/partners.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def activities(request):
    if not Services.has_access(request.user, "informationmanagement"):
        return render(request, "404.html", status=404)

    context = {
        **_base_context(request),
        "upcoming": Activity.objects.order_by("date")[:8],
        "recent": Activity.objects.order_by("-date")[:8],
    }
    return render(request, "informationmanagement/activities.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def analytics(request):
    if not Services.has_access(request.user, "informationmanagement"):
        return render(request, "404.html", status=404)

    project_total = Project.objects.count() or 1
    completed = Project.objects.filter(status="Completed").count()
    completion_rate = round((completed / project_total) * 100)
    partner_active = Partner.objects.filter(status="Active").count()
    partner_rate = round((partner_active / (Partner.objects.count() or 1)) * 100)
    reach = BeneficiaryGroup.objects.aggregate(total=Sum("households"))["total"] or 0
    activities_total = Activity.objects.count()

    insights = []
    top_category = (
        Project.objects.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
        .first()
    )
    if top_category:
        insights.append(f"Top program category: {top_category['category']}")
    if activities_total:
        insights.append(f"Recorded activities: {activities_total}")
    if not insights:
        insights.append("No analytics insights available yet.")

    context = {
        **_base_context(request),
        "kpis": [
            {"label": "Program Reach", "value": f"{reach}", "trend": "0%"},
            {"label": "Partner Engagement", "value": f"{partner_rate}%", "trend": "0%"},
            {"label": "Completion Rate", "value": f"{completion_rate}%", "trend": "0%"},
            {
                "label": "Active Projects",
                "value": f"{Project.objects.filter(status='Ongoing').count()}",
                "trend": "0%",
            },
        ],
        "insights": insights,
        "trend": [
            {"label": "Q1", "value": completion_rate},
            {"label": "Q2", "value": completion_rate},
            {"label": "Q3", "value": completion_rate},
            {"label": "Q4", "value": completion_rate},
        ],
    }
    return render(request, "informationmanagement/analytics.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def reports(request):
    if not Services.has_access(request.user, "informationmanagement"):
        return render(request, "404.html", status=404)

    context = {
        **_base_context(request),
        "reports": Report.objects.order_by("-id"),
        "templates": ReportTemplate.objects.order_by("name"),
    }
    return render(request, "informationmanagement/reports.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_lab(request):
    if not Services.has_access(request.user, "informationmanagement"):
        return render(request, "404.html", status=404)

    context = {
        **_base_context(request),
        "models": MLModel.objects.order_by("name"),
        "pipelines": MLPipeline.objects.order_by("name"),
        "experiments": MLExperiment.objects.order_by("-updated_at"),
    }
    return render(request, "informationmanagement/ml_lab.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def project_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Project created successfully.")
        return redirect("informationmanagement:information-projects")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Project",
        "cancel_url": "informationmanagement:information-projects",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def project_edit(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    project = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Project updated successfully.")
        return redirect("informationmanagement:information-projects")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Edit Project",
        "cancel_url": "informationmanagement:information-projects",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def project_delete(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted successfully.")
        return redirect("informationmanagement:information-projects")
    context = {
        **_base_context(request),
        "object": project,
        "title": "Delete Project",
        "cancel_url": "informationmanagement:information-projects",
    }
    return render(request, "informationmanagement/confirm_delete.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def beneficiary_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = BeneficiaryGroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Beneficiary group created successfully.")
        return redirect("informationmanagement:information-beneficiaries")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Beneficiary Group",
        "cancel_url": "informationmanagement:information-beneficiaries",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def beneficiary_edit(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    group = get_object_or_404(BeneficiaryGroup, pk=pk)
    form = BeneficiaryGroupForm(request.POST or None, instance=group)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Beneficiary group updated successfully.")
        return redirect("informationmanagement:information-beneficiaries")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Edit Beneficiary Group",
        "cancel_url": "informationmanagement:information-beneficiaries",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def beneficiary_delete(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    group = get_object_or_404(BeneficiaryGroup, pk=pk)
    if request.method == "POST":
        group.delete()
        messages.success(request, "Beneficiary group deleted successfully.")
        return redirect("informationmanagement:information-beneficiaries")
    context = {
        **_base_context(request),
        "object": group,
        "title": "Delete Beneficiary Group",
        "cancel_url": "informationmanagement:information-beneficiaries",
    }
    return render(request, "informationmanagement/confirm_delete.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def partner_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = PartnerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Partner created successfully.")
        return redirect("informationmanagement:information-partners")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Partner",
        "cancel_url": "informationmanagement:information-partners",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def partner_edit(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    partner = get_object_or_404(Partner, pk=pk)
    form = PartnerForm(request.POST or None, instance=partner)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Partner updated successfully.")
        return redirect("informationmanagement:information-partners")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Edit Partner",
        "cancel_url": "informationmanagement:information-partners",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def partner_delete(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    partner = get_object_or_404(Partner, pk=pk)
    if request.method == "POST":
        partner.delete()
        messages.success(request, "Partner deleted successfully.")
        return redirect("informationmanagement:information-partners")
    context = {
        **_base_context(request),
        "object": partner,
        "title": "Delete Partner",
        "cancel_url": "informationmanagement:information-partners",
    }
    return render(request, "informationmanagement/confirm_delete.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def activity_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = ActivityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Activity scheduled successfully.")
        return redirect("informationmanagement:information-activities")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Schedule Activity",
        "cancel_url": "informationmanagement:information-activities",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def activity_edit(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    activity = get_object_or_404(Activity, pk=pk)
    form = ActivityForm(request.POST or None, instance=activity)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Activity updated successfully.")
        return redirect("informationmanagement:information-activities")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Edit Activity",
        "cancel_url": "informationmanagement:information-activities",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def activity_delete(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    activity = get_object_or_404(Activity, pk=pk)
    if request.method == "POST":
        activity.delete()
        messages.success(request, "Activity deleted successfully.")
        return redirect("informationmanagement:information-activities")
    context = {
        **_base_context(request),
        "object": activity,
        "title": "Delete Activity",
        "cancel_url": "informationmanagement:information-activities",
    }
    return render(request, "informationmanagement/confirm_delete.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def report_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Report created successfully.")
        return redirect("informationmanagement:information-reports")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Report",
        "cancel_url": "informationmanagement:information-reports",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def report_edit(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    report = get_object_or_404(Report, pk=pk)
    form = ReportForm(request.POST or None, instance=report)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Report updated successfully.")
        return redirect("informationmanagement:information-reports")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Edit Report",
        "cancel_url": "informationmanagement:information-reports",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def report_delete(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    report = get_object_or_404(Report, pk=pk)
    if request.method == "POST":
        report.delete()
        messages.success(request, "Report deleted successfully.")
        return redirect("informationmanagement:information-reports")
    context = {
        **_base_context(request),
        "object": report,
        "title": "Delete Report",
        "cancel_url": "informationmanagement:information-reports",
    }
    return render(request, "informationmanagement/confirm_delete.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def report_template_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = ReportTemplateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Report template created successfully.")
        return redirect("informationmanagement:information-reports")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Report Template",
        "cancel_url": "informationmanagement:information-reports",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_model_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = MLModelForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "ML model created successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New ML Model",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_model_edit(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    model = get_object_or_404(MLModel, pk=pk)
    form = MLModelForm(request.POST or None, instance=model)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "ML model updated successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Edit ML Model",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_model_delete(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    model = get_object_or_404(MLModel, pk=pk)
    if request.method == "POST":
        model.delete()
        messages.success(request, "ML model deleted successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "object": model,
        "title": "Delete ML Model",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/confirm_delete.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_pipeline_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = MLPipelineForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pipeline created successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Pipeline",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_pipeline_edit(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    pipeline = get_object_or_404(MLPipeline, pk=pk)
    form = MLPipelineForm(request.POST or None, instance=pipeline)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pipeline updated successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Edit Pipeline",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_pipeline_delete(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    pipeline = get_object_or_404(MLPipeline, pk=pk)
    if request.method == "POST":
        pipeline.delete()
        messages.success(request, "Pipeline deleted successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "object": pipeline,
        "title": "Delete Pipeline",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/confirm_delete.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_experiment_create(request):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    form = MLExperimentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Experiment created successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Experiment",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_experiment_edit(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    experiment = get_object_or_404(MLExperiment, pk=pk)
    form = MLExperimentForm(request.POST or None, instance=experiment)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Experiment updated successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Edit Experiment",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_experiment_delete(request, pk):
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    experiment = get_object_or_404(MLExperiment, pk=pk)
    if request.method == "POST":
        experiment.delete()
        messages.success(request, "Experiment deleted successfully.")
        return redirect("informationmanagement:information-ml-lab")
    context = {
        **_base_context(request),
        "object": experiment,
        "title": "Delete Experiment",
        "cancel_url": "informationmanagement:information-ml-lab",
    }
    return render(request, "informationmanagement/confirm_delete.html", context)


# ============================================================================
# Feature 1: Contribution Allocation Management Views
# ============================================================================


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def contribution_funds_list(request):
    """List all contribution funds"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    funds = ContributionFund.objects.all()
    context = {
        **_base_context(request),
        "funds": funds,
        "title": "Contribution Funds",
    }
    return render(request, "informationmanagement/contribution_funds_list.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def contribution_fund_create(request):
    """Create new contribution fund"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    project_id = request.GET.get('project')
    initial_data = {}
    if project_id:
        try:
            project = Project.objects.get(pk=project_id)
            initial_data['project'] = project
        except Project.DoesNotExist:
            pass
    
    form = ContributionFundForm(request.POST or None, initial=initial_data)
    if request.method == "POST" and form.is_valid():
        fund = form.save(commit=False)
        fund.created_by = request.user
        fund.save()
        messages.success(request, "Contribution fund created successfully.")
        if fund.project:
            return redirect("informationmanagement:information-projects")
        return redirect("informationmanagement:contribution-funds-list")
    
    context = {
        **_base_context(request),
        "form": form,
        "title": "Create Contribution Fund",
        "cancel_url": "informationmanagement:contribution-funds-list",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def contribution_fund_detail(request, pk):
    """View fund details with allocations and expenses"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    fund = get_object_or_404(ContributionFund, pk=pk)
    allocations = fund.allocations.all()
    expenses = fund.expenses.all()
    
    context = {
        **_base_context(request),
        "fund": fund,
        "allocations": allocations,
        "expenses": expenses,
        "title": f"Fund: {fund.name}",
    }
    return render(request, "informationmanagement/contribution_fund_detail.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def fund_allocation_create(request):
    """Create new fund allocation"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    form = FundAllocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        allocation = form.save(commit=False)
        allocation.allocated_by = request.user
        allocation.save()
        messages.success(request, "Fund allocation created successfully.")
        return redirect("informationmanagement:contribution-fund-detail", pk=allocation.fund.pk)
    
    context = {
        **_base_context(request),
        "form": form,
        "title": "Create Fund Allocation",
        "cancel_url": "informationmanagement:contribution-funds-list",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def fund_expense_create(request):
    """Record fund expense"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    form = FundExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        expense.recorded_by = request.user
        expense.save()
        messages.success(request, "Fund expense recorded successfully.")
        return redirect("informationmanagement:contribution-fund-detail", pk=expense.fund.pk)
    
    context = {
        **_base_context(request),
        "form": form,
        "title": "Record Fund Expense",
        "cancel_url": "informationmanagement:contribution-funds-list",
    }
    return render(request, "informationmanagement/form.html", context)


# ============================================================================
# Feature 2: Financial Reporting Views
# ============================================================================


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def financial_dashboard(request):
    """Financial dashboard with key metrics"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import FinancialReportingService
    summary = FinancialReportingService.get_association_financial_summary()
    fund_report = FinancialReportingService.get_fund_utilization_report()
    
    context = {
        **_base_context(request),
        "summary": summary,
        "fund_report": fund_report,
        "title": "Financial Dashboard",
    }
    return render(request, "informationmanagement/financial_dashboard.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def financial_summary_report(request):
    """Association financial summary report"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import FinancialReportingService
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    summary = FinancialReportingService.get_association_financial_summary(date_from, date_to)
    
    context = {
        **_base_context(request),
        "summary": summary,
        "title": "Association Financial Summary",
    }
    return render(request, "informationmanagement/financial_summary.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def fund_utilization_report(request):
    """Fund utilization report"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import FinancialReportingService
    report_data = FinancialReportingService.get_fund_utilization_report()
    
    context = {
        **_base_context(request),
        "report_data": report_data,
        "title": "Fund Utilization Report",
    }
    return render(request, "informationmanagement/fund_utilization_report.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def monthly_contribution_report(request):
    """Monthly contribution report"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import FinancialReportingService
    from datetime import date
    
    year = request.GET.get('year', date.today().year)
    month = request.GET.get('month', date.today().month)
    
    report_data = FinancialReportingService.get_monthly_contribution_report(int(year), int(month))
    
    context = {
        **_base_context(request),
        "report_data": report_data,
        "title": "Monthly Contribution Report",
    }
    return render(request, "informationmanagement/monthly_report.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def annual_financial_report(request):
    """Annual financial report"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import FinancialReportingService
    from datetime import date
    
    year = request.GET.get('year', date.today().year)
    report_data = FinancialReportingService.get_annual_financial_report(int(year))
    
    context = {
        **_base_context(request),
        "report_data": report_data,
        "title": "Annual Financial Report",
    }
    return render(request, "informationmanagement/annual_report.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def export_financial_report(request, report_type):
    """Export financial report to PDF or Excel"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import FinancialReportingService, ExportService
    from django.http import FileResponse
    import os
    
    format_type = request.GET.get('format', 'pdf')
    
    if report_type == 'association_summary':
        data = [FinancialReportingService.get_association_financial_summary()]
        filename = f"association_summary.{format_type}"
    elif report_type == 'fund_utilization':
        data = FinancialReportingService.get_fund_utilization_report()
        filename = f"fund_utilization.{format_type}"
    else:
        return render(request, "404.html", status=404)
    
    export_path = ExportService.export_to_excel(data, report_type, filename) if format_type == 'xlsx' else ExportService.export_to_pdf(data, report_type, filename)
    
    if export_path and os.path.exists(export_path):
        return FileResponse(open(export_path, 'rb'), as_attachment=True, filename=filename)
    
    messages.error(request, "Failed to export report.")
    return redirect("informationmanagement:financial-dashboard")


# ============================================================================
# Feature 3: Member Contribution Monitoring Views
# ============================================================================


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def member_contributions_list(request):
    """List member contribution records"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import MemberContributionService
    
    filters = {
        'status_filter': request.GET.get('status_filter', 'all'),
        'member_name': request.GET.get('member_name', ''),
        'employee_id': request.GET.get('employee_id', ''),
        'department': request.GET.get('department', ''),
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
    }
    
    members = MemberContributionService.get_filtered_members(filters)
    filter_form = MemberContributionFilterForm(initial=filters)
    
    context = {
        **_base_context(request),
        "members": members,
        "filter_form": filter_form,
        "title": "Member Contributions",
    }
    return render(request, "informationmanagement/member_contributions_list.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def member_contribution_detail(request, pk):
    """View member contribution detail and statement"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import MemberContributionService
    
    member = get_object_or_404(MemberContributionRecord, pk=pk)
    statement = MemberContributionService.generate_member_statement(member)
    entries = member.ledger_entries.all()
    
    context = {
        **_base_context(request),
        "member": member,
        "statement": statement,
        "entries": entries,
        "title": f"Member Statement: {member.member_name}",
    }
    return render(request, "informationmanagement/member_contribution_detail.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def member_contribution_create(request):
    """Create member contribution record"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    project_id = request.GET.get('project')
    initial_data = {}
    if project_id:
        try:
            project = Project.objects.get(pk=project_id)
            initial_data['project'] = project
        except Project.DoesNotExist:
            pass
    
    form = MemberContributionRecordForm(request.POST or None, initial=initial_data)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Member contribution record created successfully.")
        return redirect("informationmanagement:member-contributions-list")
    
    context = {
        **_base_context(request),
        "form": form,
        "title": "Create Member Contribution Record",
        "cancel_url": "informationmanagement:member-contributions-list",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def member_contribution_entry_create(request, pk):
    """Create a new contribution entry for a member record."""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)

    member = get_object_or_404(MemberContributionRecord, pk=pk)
    form = MemberContributionEntryForm(request.POST or None, initial={"member": member})
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Contribution entry added successfully.")
        return redirect("informationmanagement:member-contribution-detail", pk=member.pk)

    context = {
        **_base_context(request),
        "form": form,
        "title": f"Add Contribution: {member.member_name}",
        "cancel_url": "informationmanagement:member-contribution-detail",
        "cancel_url_kwargs": {"pk": member.pk},
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def member_contribution_edit(request, pk):
    """Edit member contribution record"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    member = get_object_or_404(MemberContributionRecord, pk=pk)
    form = MemberContributionRecordForm(request.POST or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Member contribution record updated successfully.")
        return redirect("informationmanagement:member-contribution-detail", pk=member.pk)
    
    context = {
        **_base_context(request),
        "form": form,
        "title": f"Edit: {member.member_name}",
        "cancel_url": "informationmanagement:member-contribution-detail",
        "cancel_url_kwargs": {"pk": member.pk},
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def export_member_statement(request, pk):
    """Export individual member statement"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    from .services import MemberContributionService
    from django.http import FileResponse
    import os
    
    member = get_object_or_404(MemberContributionRecord, pk=pk)
    format_type = request.GET.get('format', 'pdf')
    
    filename = MemberContributionService.export_member_statement(member, format_type)
    
    if filename and os.path.exists(filename):
        return FileResponse(open(filename, 'rb'), as_attachment=True, filename=os.path.basename(filename))
    
    messages.error(request, "Failed to export statement.")
    return redirect("informationmanagement:member-contribution-detail", pk=pk)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def master_data_departments_list(request):
    """List master data departments"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    departments = MasterDataDepartment.objects.all()
    context = {
        **_base_context(request),
        "departments": departments,
        "title": "Master Data: Departments",
    }
    return render(request, "informationmanagement/master_data_departments_list.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def master_data_department_create(request):
    """Create new department in master data"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    form = MasterDataDepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Department created successfully.")
        return redirect("informationmanagement:master-data-departments-list")
    
    context = {
        **_base_context(request),
        "form": form,
        "title": "Create Department",
        "cancel_url": "informationmanagement:master-data-departments-list",
    }
    return render(request, "informationmanagement/form.html", context)


@login_required(login_url="/informationsystem/login")
@require_system_access
@require_system_role(["admin", "superadmin"])
def master_data_department_edit(request, pk):
    """Edit department in master data"""
    if not Services.has_access(request.user, "informationmanagement", role="admin"):
        return render(request, "404.html", status=404)
    
    department = get_object_or_404(MasterDataDepartment, pk=pk)
    form = MasterDataDepartmentForm(request.POST or None, instance=department)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Department updated successfully.")
        return redirect("informationmanagement:master-data-departments-list")
    
    context = {
        **_base_context(request),
        "form": form,
        "title": f"Edit: {department.name}",
        "cancel_url": "informationmanagement:master-data-departments-list",
    }
    return render(request, "informationmanagement/form.html", context)
