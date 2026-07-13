from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import resolve, reverse

from core.models import Systems
from core.views import core_register


class RegisterTermsModalTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.system, _ = Systems.objects.get_or_create(
            name="performanceevaluation",
            defaults={
                "description": "Performance Evaluation",
                "terms_of_service": "These are the terms.",
            },
        )

    def test_register_page_loads_shared_terms_script_for_non_scholarship_systems(self):
        request = self.factory.get("/performanceevaluation/register/")
        setattr(request, "session", {})
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        response = core_register(request, self.system.name)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("core/js/register.js", html)


class UrlPrefixTests(TestCase):
    def test_new_system_prefixes_resolve_to_the_correct_views(self):
        community_resolved = resolve("/communitymembership/dashboard/")
        information_resolved = resolve("/informationsystem/dashboard/")

        self.assertEqual(community_resolved.view_name, "communityextensionservices:ces-dashboard")
        self.assertEqual(information_resolved.view_name, "informationmanagement:information-dashboard")

    def test_system_selection_page_uses_updated_system_urls(self):
        User = get_user_model()
        user = User.objects.create_user(username="selector", password="secret123")
        self.client.force_login(user)

        session = self.client.session
        session["accessible_systems"] = [
            {"url": "communityextensionservices", "role": "admin"},
            {"url": "informationmanagement", "role": "admin"},
        ]
        session.save()

        response = self.client.get(reverse("core:system_selection"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/communitymembership/dashboard/"')
        self.assertContains(response, 'href="/informationsystem/dashboard/"')

    def test_login_pages_use_public_register_urls(self):
        community_response = self.client.get("/communitymembership/login/")
        information_response = self.client.get("/informationsystem/login/")

        self.assertEqual(community_response.status_code, 200)
        self.assertEqual(information_response.status_code, 200)
        self.assertContains(
            community_response, 'href="/communitymembership/register/"'
        )
        self.assertContains(
            information_response, 'href="/informationsystem/register/"'
        )

    def test_public_register_url_creates_canonical_membership_and_redirects(self):
        Systems.objects.get_or_create(
            name="informationmanagement",
            defaults={
                "description": "Information Management",
                "terms_of_service": "Information terms.",
            },
        )

        response = self.client.post(
            "/informationsystem/register/",
            {
                "username": "info-user",
                "password": "secret12345",
                "confirm_password": "secret12345",
                "first_name": "Info",
                "last_name": "User",
                "email": "info@example.com",
                "terms_accepted": "true",
            },
        )

        self.assertRedirects(response, "/informationsystem/login/")
        self.assertTrue(
            get_user_model().objects.filter(username="info-user").exists()
        )
        self.assertTrue(
            get_user_model()
            .objects.get(username="info-user")
            .systemmembership_set.filter(system_name="informationmanagement")
            .exists()
        )
