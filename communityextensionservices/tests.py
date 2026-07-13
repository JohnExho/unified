from django.core.management import call_command
from django.test import TestCase

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
