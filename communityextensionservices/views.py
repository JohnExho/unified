from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from core.decorators import require_system_access, require_system_role
from .forms import ActivityForm, DocumentRecordForm, DuesPaymentForm, MemberForm
from .models import (
    Activity,
    Contribution,
    DocumentRecord,
    DuesPayment,
    Member,
    MLInsight,
)
from .services import get_analytics_data, get_dashboard_data


def _has_ces_access(request):
    return request.user.has_perm(
        "communityextensionservices.access_community_extension_services_system"
    )


def _base_context(request):
    return {
        "systems": request.session.get("accessible_systems", []),
    }


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def dashboard(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    context = {
        **_base_context(request),
        **get_dashboard_data(),
    }
    return render(request, "communityextensionservices/dashboard.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def members(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    context = {
        **_base_context(request),
        "members": Member.objects.order_by("last_name", "first_name"),
    }
    return render(request, "communityextensionservices/members.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def member_create(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    form = MemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Member record created.")
        return redirect("communityextensionservices:ces-members")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Member",
        "cancel_url": "communityextensionservices:ces-members",
    }
    return render(request, "communityextensionservices/form.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def member_edit(request, pk):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    member = get_object_or_404(Member, pk=pk)
    form = MemberForm(request.POST or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Member updated.")
        return redirect("communityextensionservices:ces-members")
    context = {
        **_base_context(request),
        "form": form,
        "title": f"Edit Member · {member}",
        "cancel_url": "communityextensionservices:ces-members",
    }
    return render(request, "communityextensionservices/form.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def member_delete(request, pk):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        member.delete()
        messages.success(request, "Member deleted.")
        return redirect("communityextensionservices:ces-members")
    context = {
        **_base_context(request),
        "object": member,
        "title": "Delete Member",
        "cancel_url": "communityextensionservices:ces-members",
    }
    return render(request, "communityextensionservices/confirm_delete.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def dues(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    context = {
        **_base_context(request),
        "dues": DuesPayment.objects.select_related("member").order_by("-due_date"),
        "contributions": Contribution.objects.select_related("member").order_by(
            "-date"
        )[:10],
    }
    return render(request, "communityextensionservices/dues.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def dues_create(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    form = DuesPaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dues payment recorded.")
        return redirect("communityextensionservices:ces-dues")
    context = {
        **_base_context(request),
        "form": form,
        "title": "Record Dues",
        "cancel_url": "communityextensionservices:ces-dues",
    }
    return render(request, "communityextensionservices/form.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def activities(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    activities_qs = Activity.objects.annotate(
        attendees=Count("attendance", distinct=True),
        attended=Count(
            "attendance", filter=Q(attendance__attended=True), distinct=True
        ),
    ).order_by("-start_date")
    context = {
        **_base_context(request),
        "activities": activities_qs,
        "today": timezone.now().date(),
    }
    return render(request, "communityextensionservices/activities.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def activity_create(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    form = ActivityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Activity created.")
        return redirect("communityextensionservices:ces-activities")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Activity",
        "cancel_url": "communityextensionservices:ces-activities",
    }
    return render(request, "communityextensionservices/form.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def activity_edit(request, pk):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    activity = get_object_or_404(Activity, pk=pk)
    form = ActivityForm(request.POST or None, instance=activity)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Activity updated.")
        return redirect("communityextensionservices:ces-activities")
    context = {
        **_base_context(request),
        "form": form,
        "title": f"Edit Activity · {activity.title}",
        "cancel_url": "communityextensionservices:ces-activities",
    }
    return render(request, "communityextensionservices/form.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def activity_delete(request, pk):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    activity = get_object_or_404(Activity, pk=pk)
    if request.method == "POST":
        activity.delete()
        messages.success(request, "Activity deleted.")
        return redirect("communityextensionservices:ces-activities")
    context = {
        **_base_context(request),
        "object": activity,
        "title": "Delete Activity",
        "cancel_url": "communityextensionservices:ces-activities",
    }
    return render(request, "communityextensionservices/confirm_delete.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def documents(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    context = {
        **_base_context(request),
        "documents": DocumentRecord.objects.order_by("-created_at"),
    }
    return render(request, "communityextensionservices/documents.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def document_create(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    form = DocumentRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.uploaded_by = request.user
        document.save()
        messages.success(request, "Document stored.")
        return redirect("communityextensionservices:ces-documents")
    context = {
        **_base_context(request),
        "form": form,
        "title": "New Document",
        "cancel_url": "communityextensionservices:ces-documents",
    }
    return render(request, "communityextensionservices/form.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def analytics(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    context = {
        **_base_context(request),
        **get_analytics_data(),
    }
    return render(request, "communityextensionservices/analytics.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def reports(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    context = {
        **_base_context(request),
        "reports": DocumentRecord.objects.filter(category="report"),
    }
    return render(request, "communityextensionservices/reports.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def ml_lab(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    context = {
        **_base_context(request),
        "ml_models": MLInsight.objects.order_by("-generated_at"),
    }
    return render(request, "communityextensionservices/ml_lab.html", context)


@login_required
@require_system_access
@require_system_role(["admin", "superadmin"])
def settings(request):
    if not _has_ces_access(request):
        return render(request, "404.html", status=404)
    context = {
        **_base_context(request),
        "configuration": {
            "auto_reminders": "Enabled",
            "data_retention": "5 years",
            "ml_refresh": "Monthly",
        },
    }
    return render(request, "communityextensionservices/settings.html", context)
