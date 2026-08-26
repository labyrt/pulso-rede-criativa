from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase


User = get_user_model()


class MobileResilienceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mobileviewer",
            email="mobileviewer@test.dev",
            password="VeryStrong!123",
        )
        self.client.force_login(self.user)

    def test_authenticated_app_html_is_never_restored_from_browser_cache(self):
        response = self.client.get("/app/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertIn("private", response.headers.get("Cache-Control", ""))
        self.assertEqual(response.headers.get("Pragma"), "no-cache")
        self.assertIn("Cookie", response.headers.get("Vary", ""))

    def test_free_tier_resilience_keeps_mutations_single_shot_and_bounds_reads(self):
        script = Path(settings.BASE_DIR, "static", "webapp", "resilience.js").read_text(encoding="utf-8")

        self.assertIn('if (!retryable) return nativeFetch(input, init);', script)
        self.assertIn("const timeouts = [20000, 9000];", script)
        self.assertNotIn("32000", script)
        self.assertIn("Tentar de novo", script)
