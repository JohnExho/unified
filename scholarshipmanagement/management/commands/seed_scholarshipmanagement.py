from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from scholarshipmanagement.models import (
    StudentProfile, Scholarship, Application, Evaluation,
    Document, Notification, ScholarshipOffer, AuditLog,
)


class Command(BaseCommand):
    help = "Seed Scholarship Management with renewal-focused retention sample data."

    def _get_seed_user(self):
        User = get_user_model()

        user = User.objects.filter(username="Scholar").first()
        if user:
            return user

        return User.objects.create_user(
            username="Scholar",
            email="Scholar@example.com",
            password="Scholar6767",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        user = self._get_seed_user()
        today = timezone.now() 

        # Clean existing seed data
        AuditLog.objects.all().delete()
        Notification.objects.all().delete()
        from scholarshipmanagement.models import RecommendationModel, RenewalApplication
        RenewalApplication.objects.all().delete()
        ScholarshipOffer.objects.all().delete()
        RecommendationModel.objects.all().delete()
        Evaluation.objects.all().delete()
        Application.objects.all().delete()
        Scholarship.objects.all().delete()
        StudentProfile.objects.all().delete()

        # Create student profile
        profile = StudentProfile.objects.create(
            user=user,
            full_name="Juan Dela Cruz",
            address="123 Rizal Street, Subic",
            contact_number="+639171234567",
            family_background="Single parent household with 3 siblings.",
            school_university="Kolehiyo ng Subic",
            course_strand="BSCS",
            gpa=3.75,
            academic_awards="Dean's List 2024, Best Thesis Award",
            annual_family_income=Decimal("180000.00"),
            financial_need_score=72.0,
            province="Zambales",
            all_required_documents_uploaded=True,
            stage_1_status="complete",
            stage_1_completed_at=today,
            all_required_fields_filled=True,
            validation_checks_passed=True,
        )

        # Create a single renewal cycle record used for retention evaluation.
        renewal_cycle = Scholarship.objects.create(
            admin=user,
            created_by=user,
            name="Kolehiyo ng Subic Renewal Cycle 2026",
            description="Internal renewal cycle for continuing scholars and passing-grade retention checks.",
            category="merit_based",
            scholarship_type="government",
            award_amount=Decimal("1.00"),
            number_of_slots=9999,
            renewable=True,
            eligibility_rules={"renewal_only": True, "min_gpa": 2.0},
            required_documents=["transcript"],
            status="published",
            application_start_date=today - timedelta(days=5),
            application_end_date=today + timedelta(days=25),
        )
        self.stdout.write(f"  Created renewal cycle: {renewal_cycle.name}")

        # Create a sample application
        app = Application.objects.create(
            student=user,
            scholarship=renewal_cycle,
            status='under_review',
            motivation_essay="I am requesting scholarship renewal and confirming compliance with passing-grade requirements.",
            achievements="Maintained passing grades and completed required units this term.",
            submitted_at=today - timedelta(days=2),
        )

        # Create evaluation (simplified for single-school renewal)
        Evaluation.objects.create(
            application=app,
            reviewer=user,
            status='completed',
            prediction_label='Retain',
            prediction_confidence=85.5,
            recommendation='retain',
            reviewer_comments='Strong academic background and clear motivation. Recommended for retention.',
        )

        # Notification
        Notification.objects.create(
            recipient=user,
            notification_type='application_status',
            title='Renewal Assessment In Progress',
            message=f'Your renewal assessment for "{renewal_cycle.name}" is under review.',
            related_application=app,
            related_scholarship=renewal_cycle,
        )

        Notification.objects.create(
            recipient=user,
            notification_type='stage_unlocked',
            title='Renewal Profile Complete',
            message='Your profile is complete. You can now proceed with renewal retention review.',
        )

        self.stdout.write(self.style.SUCCESS(
            f"\nScholarship Management seeded successfully. "
            f"Created 1 renewal cycle, 1 renewal application, 1 evaluation."
        ))
