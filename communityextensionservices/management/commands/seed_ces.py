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
        if Member.objects.exists():
            self.stdout.write(self.style.WARNING("CES data already seeded."))
            return

        today = timezone.now().date()

        Service.objects.create(
            name="Faculty Outreach Program",
            description="Extension and community engagement activities.",
            start_date=today - timedelta(days=90),
            end_date=today + timedelta(days=120),
        )

        members = [
            Member(
                first_name="Maria",
                last_name="Reyes",
                email="mreyes@example.com",
                classification="faculty",
                status="active",
                joined_date=today - timedelta(days=180),
                department="Education",
                engagement_score=82.5,
                churn_risk_score=12.4,
                predicted_status="Active",
                cluster_label="Engaged",
            ),
            Member(
                first_name="Joan",
                last_name="Santos",
                email="jsantos@example.com",
                classification="non_teaching",
                status="active",
                joined_date=today - timedelta(days=95),
                department="Administration",
                engagement_score=71.2,
                churn_risk_score=22.9,
                predicted_status="Active",
                cluster_label="Steady",
            ),
            Member(
                first_name="Leonardo",
                last_name="Cruz",
                email="lcruz@example.com",
                classification="retired",
                status="inactive",
                joined_date=today - timedelta(days=420),
                department="Research",
                engagement_score=45.0,
                churn_risk_score=68.3,
                predicted_status="At Risk",
                cluster_label="Dormant",
            ),
            Member(
                first_name="Angel",
                last_name="Lim",
                email="alim@example.com",
                classification="associate",
                status="active",
                joined_date=today - timedelta(days=60),
                department="Extension",
                engagement_score=88.4,
                churn_risk_score=9.8,
                predicted_status="Active",
                cluster_label="Champion",
            ),
        ]
        Member.objects.bulk_create(members)

        for member in Member.objects.all():
            MembershipHistory.objects.create(member=member, status=member.status)

        Activity.objects.bulk_create(
            [
                Activity(
                    title="Membership Orientation",
                    category="Onboarding",
                    start_date=today + timedelta(days=7),
                    end_date=today + timedelta(days=7),
                    location="Conference Room A",
                    status="scheduled",
                    description="Orientation for new association members.",
                ),
                Activity(
                    title="Community Impact Forum",
                    category="Engagement",
                    start_date=today - timedelta(days=12),
                    end_date=today - timedelta(days=12),
                    location="Main Hall",
                    status="completed",
                    description="Sharing of community service outcomes.",
                ),
            ]
        )

        activity = Activity.objects.first()
        for member in Member.objects.all():
            Attendance.objects.create(
                member=member,
                activity=activity,
                attended=True,
                role="Participant",
            )

        for member in Member.objects.all():
            DuesPayment.objects.create(
                member=member,
                amount=500.00,
                due_date=today + timedelta(days=15),
                status="pending",
                method="cash",
                late_payment_risk=15.0,
            )

        Contribution.objects.create(
            member=Member.objects.first(),
            title="Volunteer Hours",
            category="volunteer",
            amount=0,
            date=today - timedelta(days=30),
            remarks="Facilitated data collection training.",
        )

        DocumentRecord.objects.bulk_create(
            [
                DocumentRecord(
                    title="Membership Policy Handbook",
                    category="policy",
                    summary="Updated membership policy for CES.",
                    is_sensitive=False,
                ),
                DocumentRecord(
                    title="Q4 2025 Financial Report",
                    category="report",
                    summary="Summary of dues and contribution performance.",
                    is_sensitive=True,
                ),
            ]
        )

        MLInsight.objects.bulk_create(
            [
                MLInsight(
                    name="Retention Forecast",
                    target="Membership status",
                    algorithm="Gradient Boosting",
                    status="ready",
                    score=0.842,
                    notes="Pilot model using dues timeliness + engagement scores.",
                ),
                MLInsight(
                    name="Engagement Segmentation",
                    target="Member clusters",
                    algorithm="K-Means",
                    status="training",
                    score=0.612,
                    notes="Clustering on participation and contribution signals.",
                ),
            ]
        )

        self.stdout.write(self.style.SUCCESS("CES demo data seeded."))
