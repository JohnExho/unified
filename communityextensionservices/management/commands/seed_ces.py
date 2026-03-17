from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from communityextensionservices.models import (
    Activity,
    Attendance,
    Contribution,
    DocumentRecord,
    DuesPayment,
    Member,
    MembershipHistory,
    MLInsight,
    Service,
)


class Command(BaseCommand):
    help = "Seed Community Extension Services data for demo."

    def handle(self, *args, **options):
        today = timezone.now().date()

        Service.objects.get_or_create(
            name="Faculty Outreach Program",
            defaults={
                "description": "Extension and community engagement activities.",
                "start_date": today - timedelta(days=90),
                "end_date": today + timedelta(days=120),
            },
        )

        members = [
            {
                "first_name": "Maria",
                "last_name": "Reyes",
                "email": "mreyes@example.com",
                "classification": "faculty",
                "status": "active",
                "joined_date": today - timedelta(days=180),
                "department": "Education",
                "engagement_score": 82.5,
                "churn_risk_score": 12.4,
                "predicted_status": "Active",
                "cluster_label": "Engaged",
            },
            {
                "first_name": "Joan",
                "last_name": "Santos",
                "email": "jsantos@example.com",
                "classification": "non_teaching",
                "status": "active",
                "joined_date": today - timedelta(days=95),
                "department": "Administration",
                "engagement_score": 71.2,
                "churn_risk_score": 22.9,
                "predicted_status": "Active",
                "cluster_label": "Steady",
            },
            {
                "first_name": "Leonardo",
                "last_name": "Cruz",
                "email": "lcruz@example.com",
                "classification": "retired",
                "status": "inactive",
                "joined_date": today - timedelta(days=420),
                "department": "Research",
                "engagement_score": 45.0,
                "churn_risk_score": 68.3,
                "predicted_status": "At Risk",
                "cluster_label": "Dormant",
            },
            {
                "first_name": "Angel",
                "last_name": "Lim",
                "email": "alim@example.com",
                "classification": "associate",
                "status": "active",
                "joined_date": today - timedelta(days=60),
                "department": "Extension",
                "engagement_score": 88.4,
                "churn_risk_score": 9.8,
                "predicted_status": "Active",
                "cluster_label": "Champion",
            },
            {
                "first_name": "Carla",
                "last_name": "Villanueva",
                "email": "cvillanueva@example.com",
                "classification": "faculty",
                "status": "active",
                "joined_date": today - timedelta(days=210),
                "department": "Social Sciences",
                "engagement_score": 76.3,
                "churn_risk_score": 18.1,
                "predicted_status": "Active",
                "cluster_label": "Reliable",
            },
            {
                "first_name": "Paolo",
                "last_name": "Mendoza",
                "email": "pmendoza@example.com",
                "classification": "non_teaching",
                "status": "inactive",
                "joined_date": today - timedelta(days=300),
                "department": "Operations",
                "engagement_score": 54.8,
                "churn_risk_score": 47.2,
                "predicted_status": "At Risk",
                "cluster_label": "Needs Support",
            },
        ]

        created_members = 0
        for member_data in members:
            member, created = Member.objects.get_or_create(
                email=member_data["email"],
                defaults=member_data,
            )
            if created:
                created_members += 1
            else:
                for field, value in member_data.items():
                    setattr(member, field, value)
                member.save()

        for member in Member.objects.all():
            MembershipHistory.objects.get_or_create(member=member, status=member.status)

        Activity.objects.update_or_create(
            title="Membership Orientation",
            defaults={
                "category": "Onboarding",
                "start_date": today + timedelta(days=7),
                "end_date": today + timedelta(days=7),
                "location": "Conference Room A",
                "status": "scheduled",
                "description": "Orientation for new association members.",
            },
        )
        Activity.objects.update_or_create(
            title="Community Impact Forum",
            defaults={
                "category": "Engagement",
                "start_date": today - timedelta(days=12),
                "end_date": today - timedelta(days=12),
                "location": "Main Hall",
                "status": "completed",
                "description": "Sharing of community service outcomes.",
            },
        )

        activity = Activity.objects.first()
        for member in Member.objects.all():
            Attendance.objects.get_or_create(
                member=member,
                activity=activity,
                defaults={
                    "attended": True,
                    "role": "Participant",
                },
            )

        for member in Member.objects.all():
            DuesPayment.objects.update_or_create(
                member=member,
                due_date=today + timedelta(days=15),
                defaults={
                    "amount": 500.00,
                    "status": "pending",
                    "method": "cash",
                    "late_payment_risk": 15.0,
                },
            )

        first_member = Member.objects.order_by("id").first()
        if (
            first_member
            and not Contribution.objects.filter(
                member=first_member,
                title="Volunteer Hours",
                date=today - timedelta(days=30),
            ).exists()
        ):
            Contribution.objects.create(
                member=first_member,
                title="Volunteer Hours",
                category="volunteer",
                amount=0,
                date=today - timedelta(days=30),
                remarks="Facilitated data collection training.",
            )

        DocumentRecord.objects.update_or_create(
            title="Membership Policy Handbook",
            defaults={
                "category": "policy",
                "summary": "Updated membership policy for CES.",
                "is_sensitive": False,
            },
        )
        DocumentRecord.objects.update_or_create(
            title="Q4 2025 Financial Report",
            defaults={
                "category": "report",
                "summary": "Summary of dues and contribution performance.",
                "is_sensitive": True,
            },
        )

        MLInsight.objects.update_or_create(
            name="Retention Forecast",
            defaults={
                "target": "Membership status",
                "algorithm": "Gradient Boosting",
                "status": "ready",
                "score": 0.842,
                "notes": "Pilot model using dues timeliness + engagement scores.",
            },
        )
        MLInsight.objects.update_or_create(
            name="Engagement Segmentation",
            defaults={
                "target": "Member clusters",
                "algorithm": "K-Means",
                "status": "training",
                "score": 0.612,
                "notes": "Clustering on participation and contribution signals.",
            },
        )

        total_members = Member.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"CES demo data seeded/updated. created_members={created_members} total_members={total_members}"
            )
        )
