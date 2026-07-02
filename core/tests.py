from django.test import TestCase, RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

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
