from datetime import timedelta
from decimal import Decimal
import os
from django.conf import settings
from django.db import models
from django.db.models import Count
from django.utils import timezone
from .models import (
    Member,
    DuesPayment,
    Activity,
    DocumentRecord,
    MLInsight,
    Attendance,
    Contribution,
)
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


class CESClusteringService:
    """Basic K-Means clustering for CES member segmentation."""

    MODEL_PATH = os.path.join(
        settings.BASE_DIR,
        "communityextensionservices",
        "ml_models",
        "member_kmeans.joblib",
    )

    @staticmethod
    def _build_member_features(lookback_days=365):
        import numpy as np

        today = timezone.now().date()
        start_date = today - timedelta(days=lookback_days)
        rows = []

        members = Member.objects.all().order_by("id")
        for member in members:
            dues_qs = DuesPayment.objects.filter(
                member=member, due_date__gte=start_date
            )
            dues_total = dues_qs.count()
            dues_paid = dues_qs.filter(status="paid").count()
            dues_overdue = dues_qs.filter(status="overdue").count()

            attendance_qs = Attendance.objects.filter(
                member=member,
                activity__start_date__gte=start_date,
            )
            attendance_total = attendance_qs.count()
            attendance_present = attendance_qs.filter(attended=True).count()

            contribution_qs = Contribution.objects.filter(
                member=member, date__gte=start_date
            )
            contribution_count = contribution_qs.count()
            contribution_amount = (
                contribution_qs.aggregate(total=models.Sum("amount")).get("total") or 0
            )

            payment_ratio = (dues_paid / dues_total) if dues_total else 0
            overdue_ratio = (dues_overdue / dues_total) if dues_total else 0
            attendance_ratio = (
                (attendance_present / attendance_total) if attendance_total else 0
            )
            tenure_days = max(0, (today - member.joined_date).days)

            features = np.array(
                [
                    float(tenure_days),
                    float(payment_ratio),
                    float(overdue_ratio),
                    float(attendance_ratio),
                    float(contribution_count),
                    float(contribution_amount),
                    1.0 if member.status == "active" else 0.0,
                    1.0 if member.classification == "faculty" else 0.0,
                ]
            )

            rows.append(
                {
                    "member": member,
                    "features": features,
                    "payment_ratio": payment_ratio,
                    "attendance_ratio": attendance_ratio,
                    "overdue_ratio": overdue_ratio,
                    "contribution_count": contribution_count,
                }
            )

        return rows

    @staticmethod
    def _load_model_artifact():
        import joblib

        if not os.path.exists(CESClusteringService.MODEL_PATH):
            return None
        return joblib.load(CESClusteringService.MODEL_PATH)

    @staticmethod
    def train_kmeans_model(k=3, lookback_days=365):
        import numpy as np
        import joblib
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
        from sklearn.preprocessing import StandardScaler

        rows = CESClusteringService._build_member_features(lookback_days=lookback_days)
        if len(rows) < max(6, k):
            return {
                "trained": False,
                "reason": "Not enough member samples for clustering",
                "samples": len(rows),
            }

        X = np.vstack([row["features"] for row in rows])

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = model.fit_predict(X_scaled)

        silhouette = None
        if len(set(labels.tolist())) > 1:
            silhouette = round(float(silhouette_score(X_scaled, labels)), 4)

        os.makedirs(os.path.dirname(CESClusteringService.MODEL_PATH), exist_ok=True)
        artifact = {
            "model": model,
            "scaler": scaler,
            "k": k,
            "lookback_days": lookback_days,
            "trained_at": timezone.now().isoformat(),
        }
        joblib.dump(artifact, CESClusteringService.MODEL_PATH)

        MLInsight.objects.update_or_create(
            name="CES Member Segmentation",
            defaults={
                "target": "Member Clusters",
                "algorithm": "K-Means Clustering",
                "status": "ready",
                "score": Decimal(str(silhouette if silhouette is not None else 0)),
                "notes": f"k={k}, samples={len(rows)}"
                + (f", silhouette={silhouette}" if silhouette is not None else ""),
            },
        )

        return {
            "trained": True,
            "samples": len(rows),
            "clusters": k,
            "silhouette": silhouette,
            "model_path": CESClusteringService.MODEL_PATH,
        }

    @staticmethod
    def run_member_clustering():
        import numpy as np

        artifact = CESClusteringService._load_model_artifact()
        if not artifact:
            return []

        model = artifact["model"]
        scaler = artifact["scaler"]
        lookback_days = artifact.get("lookback_days", 365)

        rows = CESClusteringService._build_member_features(lookback_days=lookback_days)
        if not rows:
            return []

        X = np.vstack([row["features"] for row in rows])
        labels = model.predict(scaler.transform(X))

        assignments = []
        for row, label in zip(rows, labels):
            member = row["member"]
            cluster_label = f"Cluster {int(label)}"

            engagement_score = (
                (row["payment_ratio"] * 45)
                + (row["attendance_ratio"] * 35)
                + (min(row["contribution_count"], 10) / 10 * 20)
            )
            engagement_score = round(max(0.0, min(100.0, engagement_score)), 2)
            churn_risk = round(
                max(
                    0.0,
                    min(100.0, 100.0 - engagement_score + (row["overdue_ratio"] * 20)),
                ),
                2,
            )

            member.cluster_label = cluster_label
            member.engagement_score = Decimal(str(engagement_score))
            member.churn_risk_score = Decimal(str(churn_risk))
            member.predicted_status = "active" if engagement_score >= 60 else "inactive"
            member.save(
                update_fields=[
                    "cluster_label",
                    "engagement_score",
                    "churn_risk_score",
                    "predicted_status",
                ]
            )

            assignments.append(
                {
                    "member": member,
                    "cluster_label": cluster_label,
                    "engagement_score": engagement_score,
                    "churn_risk_score": churn_risk,
                }
            )

        return sorted(
            assignments, key=lambda item: item["engagement_score"], reverse=True
        )

    @staticmethod
    def _fallback_clusters(limit=8):
        members = Member.objects.order_by("-created_at")[:limit]
        return [
            {
                "member": member,
                "cluster_label": member.cluster_label or "Unassigned",
                "engagement_score": float(member.engagement_score or 0),
                "churn_risk_score": float(member.churn_risk_score or 0),
            }
            for member in members
        ]

    @staticmethod
    def get_dashboard_snapshot(limit=8):
        model_ready = CESClusteringService._load_model_artifact() is not None
        clusters = []
        uses_fallback = False

        if model_ready:
            clusters = CESClusteringService.run_member_clustering()

        if not clusters:
            clusters = CESClusteringService._fallback_clusters(limit=limit)
            uses_fallback = True

        return {
            "model_ready": model_ready,
            "uses_fallback": uses_fallback,
            "clusters": clusters[:limit],
        }
