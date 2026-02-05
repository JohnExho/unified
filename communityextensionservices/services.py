from datetime import timedelta
from django.db import models
from django.db.models import Count
from django.utils import timezone
from .models import Member, DuesPayment, Activity, DocumentRecord, MLInsight
from .utils import percent_change


def get_dashboard_data():
    today = timezone.now().date()
    last_30 = today - timedelta(days=30)
    prev_30 = today - timedelta(days=60)

    total_members = Member.objects.count()
    active_members = Member.objects.filter(status="active").count()
    new_members = Member.objects.filter(created_at__date__gte=last_30).count()
    previous_new = Member.objects.filter(
        created_at__date__gte=prev_30, created_at__date__lt=last_30
    ).count()

    pending_dues = DuesPayment.objects.filter(status="pending").count()
    overdue_dues = DuesPayment.objects.filter(status="overdue").count()
    activities_upcoming = Activity.objects.filter(start_date__gte=today).count()

    stats = [
        {
            "label": "Total Members",
            "value": total_members,
            "delta": percent_change(new_members, previous_new),
            "trend": "up" if new_members >= previous_new else "down",
        },
        {
            "label": "Active Members",
            "value": active_members,
            "delta": 0,
            "trend": "up",
        },
        {
            "label": "Pending Dues",
            "value": pending_dues,
            "delta": 0,
            "trend": "down" if overdue_dues else "up",
        },
        {
            "label": "Upcoming Activities",
            "value": activities_upcoming,
            "delta": 0,
            "trend": "up",
        },
    ]

    status_breakdown = (
        Member.objects.values("status").annotate(count=Count("id")).order_by("status")
    )
    dues_summary = (
        DuesPayment.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    upcoming_activities = Activity.objects.filter(start_date__gte=today).order_by(
        "start_date"
    )[:5]
    recent_members = Member.objects.order_by("-created_at")[:5]

    ml_insights = MLInsight.objects.order_by("-generated_at")[:4]

    return {
        "stats": stats,
        "status_breakdown": status_breakdown,
        "dues_summary": dues_summary,
        "upcoming_activities": upcoming_activities,
        "recent_members": recent_members,
        "documents_count": DocumentRecord.objects.count(),
        "ml_count": MLInsight.objects.count(),
        "ml_insights": ml_insights,
    }


def get_analytics_data():
    total_members = Member.objects.count() or 1
    active_members = Member.objects.filter(status="active").count()
    inactive_members = Member.objects.exclude(status="active").count()

    overdue = DuesPayment.objects.filter(status="overdue").count()
    pending = DuesPayment.objects.filter(status="pending").count()
    engagement_avg = (
        Member.objects.exclude(engagement_score__isnull=True)
        .aggregate(avg=models.Avg("engagement_score"))
        .get("avg")
    )

    return {
        "kpis": [
            {
                "label": "Retention Rate",
                "value": f"{round(active_members / total_members * 100)}%",
                "trend": "stable",
            },
            {
                "label": "Inactive Members",
                "value": inactive_members,
                "trend": "watch",
            },
            {
                "label": "Overdue Dues",
                "value": overdue,
                "trend": "risk",
            },
            {
                "label": "Engagement Avg",
                "value": f"{round(engagement_avg or 0, 2)}",
                "trend": "stable",
            },
        ],
        "membership_split": [
            {"label": "Active", "value": active_members},
            {"label": "Inactive", "value": inactive_members},
        ],
        "dues_health": [
            {"label": "Pending", "value": pending},
            {"label": "Overdue", "value": overdue},
            {
                "label": "Paid",
                "value": DuesPayment.objects.filter(status="paid").count(),
            },
        ],
        "insights": [
            "Faculty members show higher on-time payment rates.",
            "Associate members are most active in program attendance.",
            "Retired segment benefits from quarterly engagement check-ins.",
        ],
    }
