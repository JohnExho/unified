from decimal import Decimal

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import StudentProfile


class ScholarshipSeederTests(TestCase):
    def test_seed_scholarshipmanagement_can_run_twice(self):
        User = get_user_model()

        call_command("seed_scholarshipmanagement")
        call_command("seed_scholarshipmanagement")

        self.assertEqual(1, User.objects.filter(username="Scholar").count())


class ScholarshipMlModelPageTests(TestCase):
    def test_ml_model_page_route_is_available(self):
        self.assertEqual(reverse("scholarshipmanagement:ml_model"), "/scholarshipmanagement/ml-model/")


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
