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
    help = "Seed Scholarship Management with sample scholarships, profiles, and applications."

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

        # Create scholarships
        scholarships_data = [
            {
                "name": "DOST-SEI Merit Scholarship",
                "description": "Full scholarship for science and engineering students with outstanding academic performance.",
                "category": "merit_based",
                "scholarship_type": "government",
                "award_amount": Decimal("60000.00"),
                "number_of_slots": 50,
                "renewable": True,
                "eligibility_rules": {"min_gpa": 3.5, "required_course": ["BSCS", "BSIT", "BSECE"]},
                "required_documents": ["government_id", "transcript"],
                "status": "published",
                "application_start_date": today - timedelta(days=5),
                "application_end_date": today + timedelta(days=25),
            },
            {
                "name": "Ayala Foundation Need-Based Grant",
                "description": "Financial assistance for deserving students from low-income families.",
                "category": "need_based",
                "scholarship_type": "corporate",
                "award_amount": Decimal("40000.00"),
                "number_of_slots": 30,
                "renewable": False,
                "eligibility_rules": {"max_annual_income": 250000},
                "required_documents": ["government_id", "transcript", "income_proof"],
                "status": "published",
                "application_start_date": today - timedelta(days=10),
                "application_end_date": today + timedelta(days=20),
            },
            {
                "name": "SMC Talent Arts Scholarship",
                "description": "For students with exceptional talent in visual arts, music, or cultural performance.",
                "category": "talent_based",
                "scholarship_type": "private",
                "award_amount": Decimal("30000.00"),
                "number_of_slots": 15,
                "renewable": False,
                "eligibility_rules": {},
                "required_documents": ["government_id", "transcript"],
                "status": "published",
                "application_start_date": today - timedelta(days=3),
                "application_end_date": today + timedelta(days=30),
            },
            {
                "name": "LGU Zambales Province Scholarship",
                "description": "Scholarship exclusively for residents of Zambales province.",
                "category": "need_based",
                "scholarship_type": "government",
                "award_amount": Decimal("25000.00"),
                "number_of_slots": 100,
                "renewable": True,
                "eligibility_rules": {"required_province": ["Zambales"]},
                "required_documents": ["government_id", "income_proof"],
                "status": "published",
                "application_start_date": today - timedelta(days=15),
                "application_end_date": today + timedelta(days=15),
            },
            {
                "name": "Historical Archives Grant (Closed)",
                "description": "Closed scholarship for records.",
                "category": "merit_based",
                "scholarship_type": "organization",
                "award_amount": Decimal("20000.00"),
                "number_of_slots": 10,
                "renewable": False,
                "eligibility_rules": {},
                "required_documents": ["government_id"],
                "status": "closed",
                "application_start_date": today - timedelta(days=60),
                "application_end_date": today - timedelta(days=30),
            },
        ]

        scholarships = []
        for data in scholarships_data:
            s = Scholarship.objects.create(
                admin=user,
                created_by=user,
                **data
            )
            scholarships.append(s)
            self.stdout.write(f"  Created scholarship: {s.name}")

        # Create a sample application
        app = Application.objects.create(
            student=user,
            scholarship=scholarships[0],
            status='under_review',
            motivation_essay="I have always been passionate about computer science and wish to contribute to Philippine technology sector.",
            achievements="Dean's List, ICPC Regional Finalist, Open-source contributor.",
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
            title='Application Under Review',
            message=f'Your application for "{scholarships[0].name}" is under review.',
            related_application=app,
            related_scholarship=scholarships[0],
        )

        Notification.objects.create(
            recipient=user,
            notification_type='stage_unlocked',
            title='Stage 2 Unlocked!',
            message='Your profile is complete. You can now browse and apply for scholarships.',
        )

        self.stdout.write(self.style.SUCCESS(
            f"\nScholarship Management seeded successfully. "
            f"Created {len(scholarships)} scholarships, 1 application, 1 evaluation."
        ))
