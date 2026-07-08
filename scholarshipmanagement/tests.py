from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ScholarshipSeederTests(TestCase):
    def test_seed_scholarshipmanagement_can_run_twice(self):
        User = get_user_model()

        call_command("seed_scholarshipmanagement")
        call_command("seed_scholarshipmanagement")

        self.assertEqual(1, User.objects.filter(username="Scholar").count())


class ScholarshipMlModelPageTests(TestCase):
    def test_ml_model_page_route_is_available(self):
        self.assertEqual(reverse("scholarshipmanagement:ml_model"), "/scholarshipmanagement/ml-model/")
