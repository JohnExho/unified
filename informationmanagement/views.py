from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.text import slugify
from django.contrib import messages
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


@login_required(login_url="/informationmanagement/login")
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
    }
    return render(request, "informationmanagement/dashboard.html", context)


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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


@login_required(login_url="/informationmanagement/login")
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
