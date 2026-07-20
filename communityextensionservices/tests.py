from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import SystemMembership
from .models import Contribution, Member, Service


class SeedCETestCase(TestCase):
    def test_seed_ces_creates_association_member_contributions(self):
        call_command("seed_ces")

        service = Service.objects.filter(name="KNS Faculty and Employee Association").first()
        self.assertIsNotNone(service)
        self.assertIn("association fund", service.description.lower())

        members = Member.objects.count()
        contributions = Contribution.objects.filter(title="Association Contribution").count()
        self.assertEqual(contributions, members)

        for contribution in Contribution.objects.filter(title="Association Contribution"):
            self.assertEqual(contribution.amount, 50.00)
            self.assertIn("payday", contribution.remarks.lower())


class PublicLoginRedirectTests(TestCase):
    def test_dashboard_redirects_to_public_communitymembership_login(self):
        response = self.client.get("/communitymembership/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/communitymembership/login?next=/communitymembership/dashboard/",
        )


class CESAccessTests(TestCase):
    def test_regular_user_with_membership_can_access_dashboard(self):
        User = get_user_model()
        user = User.objects.create_user(username="cesuser", password="secret123")
        SystemMembership.objects.create(user=user, system_name="communityextensionservices", system_role="user")

        self.client.force_login(user)
        session = self.client.session
        session["current_system"] = "communityextensionservices"
        session.save()

        response = self.client.get(reverse("communityextensionservices:ces-dashboard"))

        self.assertEqual(response.status_code, 200)
