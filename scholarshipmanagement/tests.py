from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import SystemMembership
from .models import Scholarship, StudentProfile
from .ml_recommendation import build_overall_prediction_summary, predict_retention


class ScholarshipSeederTests(TestCase):
    def test_seed_scholarshipmanagement_can_run_twice(self):
        User = get_user_model()

        call_command("seed_scholarshipmanagement")
        call_command("seed_scholarshipmanagement")

        self.assertEqual(1, User.objects.filter(username="Scholar").count())


class ScholarshipMlModelPageTests(TestCase):
    def test_ml_model_page_route_is_available(self):
        self.assertEqual(reverse("scholarshipmanagement:ml_model"), "/scholarshipmanagement/ml-model/")

    def test_ml_model_page_requires_admin_access(self):
        User = get_user_model()
        user = User.objects.create_user(username="studentuser", password="secret123")
        self.client.force_login(user)

        response = self.client.get(reverse("scholarshipmanagement:ml_model"))

        self.assertEqual(response.status_code, 404)


class AdminMonitoringTests(TestCase):
    def test_admin_monitoring_route_is_available(self):
        self.assertEqual(reverse("scholarshipmanagement:admin_monitoring"), "/scholarshipmanagement/admin/monitoring/")

    def test_admin_monitoring_requires_admin_access(self):
        User = get_user_model()
        user = User.objects.create_user(username="studentuser2", password="secret123")
        self.client.force_login(user)

        response = self.client.get(reverse("scholarshipmanagement:admin_monitoring"))

        self.assertEqual(response.status_code, 404)


class StudentProfileMlReadinessTests(TestCase):
    def test_profile_with_basic_fields_is_ml_ready(self):
        User = get_user_model()
        user = User.objects.create_user(username="mluser", password="secret123")
        profile = StudentProfile.objects.create(user=user)

        profile.full_name = "Jane Doe"
        profile.course_strand = "BSCS"
        profile.gpa = 3.5
        profile.annual_family_income = Decimal("200000")
        profile.province = "Cebu"
        profile.save()

        self.assertTrue(profile.is_ml_ready)

    def test_profile_without_required_fields_is_not_ml_ready(self):
        User = get_user_model()
        user = User.objects.create_user(username="mluser2", password="secret123")
        profile = StudentProfile.objects.create(user=user)

        self.assertFalse(profile.is_ml_ready)

    def test_build_overall_prediction_summary_returns_aggregate_metrics(self):
        User = get_user_model()
        user = User.objects.create_user(username="mluser3", password="secret123")
        profile = StudentProfile.objects.create(
            user=user,
            full_name="Jane Doe",
            course_strand="BSCS",
            gpa=3.5,
            annual_family_income=Decimal("200000"),
            province="Cebu",
        )
        scholarship = Scholarship.objects.create(
            name="Aggregate Test Scholarship",
            description="Test scholarship",
            category="merit_based",
            scholarship_type="government",
            status="published",
            award_amount=Decimal("10000.00"),
            number_of_slots=5,
            renewable=False,
            eligibility_rules={"min_gpa": 3.0},
            required_documents=["government_id"],
            application_start_date=timezone.now() - timedelta(days=1),
            application_end_date=timezone.now() + timedelta(days=10),
        )

        summary = build_overall_prediction_summary([profile], [scholarship])

        self.assertEqual(summary["total_profiles"], 1)
        self.assertEqual(summary["total_scholarships"], 1)
        self.assertEqual(summary["top_scholarship"], scholarship)
        self.assertGreaterEqual(summary["average_match_score"], 0)

    def test_predict_retention_returns_one_of_expected_labels(self):
        User = get_user_model()
        user = User.objects.create_user(username="mluser4", password="secret123")
        profile = StudentProfile.objects.create(
            user=user,
            full_name="John Smith",
            course_strand="BSIT",
            gpa=3.2,
            annual_family_income=Decimal("180000"),
            province="Cebu",
            failed_subjects=2,
            units_enrolled=24,
            attendance_rate=78.0,
            socioeconomic_status='low',
        )

        prediction = predict_retention(profile, scholarship_type='merit_based')

        self.assertIn(prediction['label'], ['Retain', 'At-Risk', 'Failed'])
        self.assertGreaterEqual(prediction['confidence'], 0)

    def test_predict_retention_marks_gpa_275_as_at_risk(self):
        User = get_user_model()
        user = User.objects.create_user(username="mluser5", password="secret123")
        profile = StudentProfile.objects.create(
            user=user,
            full_name="Jane Doe",
            course_strand="BSIT",
            gpa=2.75,
            annual_family_income=Decimal("150000"),
            province="Cebu",
            failed_subjects=0,
            units_enrolled=24,
            attendance_rate=95.0,
            socioeconomic_status='low',
        )

        prediction = predict_retention(profile, scholarship_type='merit_based')

        self.assertEqual(prediction['label'], 'At-Risk')


class IntakeRetentionPreviewTests(TestCase):
    def test_preview_endpoint_returns_live_retention_prediction(self):
        User = get_user_model()
        user = User.objects.create_user(username="adminpreview", password="secret123")
        SystemMembership.objects.create(
            user=user,
            system_name="scholarshipmanagement",
            system_role="admin",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("scholarshipmanagement:intake_retention_preview"),
            {
                "username": "preview-student",
                "email": "preview@example.com",
                "password": "secret12345",
                "full_name": "Preview Student",
                "contact_number": "+639171234567",
                "address": "Test Address",
                "school_university": "KNS",
                "course_strand": "BSIT",
                "province": "Zambales",
                "gpa": "3.10",
                "annual_family_income": "120000",
                "failed_subjects": "2",
                "units_enrolled": "21",
                "attendance_rate": "77.5",
                "socioeconomic_status": "low",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn(payload["prediction"]["label"], ["Retain", "At-Risk", "Failed"])
        self.assertGreaterEqual(payload["prediction"]["confidence"], 0)

    def test_preview_endpoint_does_not_error_for_incomplete_input(self):
        User = get_user_model()
        user = User.objects.create_user(username="adminpreview2", password="secret123")
        SystemMembership.objects.create(
            user=user,
            system_name="scholarshipmanagement",
            system_role="admin",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("scholarshipmanagement:intake_retention_preview"),
            {
                "gpa": "3.10",
                "failed_subjects": "",
                "units_enrolled": "21",
                "attendance_rate": "77.5",
                "socioeconomic_status": "low",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("failed_subjects", payload["errors"])
