from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


User = get_user_model()


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
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

    def test_app_uses_native_fetch_and_loads_lifecycle_recovery(self):
        response = self.client.get("/app/")
        html = response.content.decode("utf-8")

        self.assertIn("webapp/app.js", html)
        self.assertIn("webapp/lifecycle-recovery.js", html)
        self.assertNotIn("webapp/resilience.js", html)
        self.assertLess(html.index("webapp/app.js"), html.index("webapp/lifecycle-recovery.js"))

    def test_feed_watchdog_recovers_stalled_dom_without_reloading_document(self):
        script = Path(settings.BASE_DIR, "static", "webapp", "lifecycle-recovery.js").read_text(encoding="utf-8")

        self.assertIn('window.addEventListener("pageshow"', script)
        self.assertIn("event.persisted", script)
        self.assertIn("new AbortController()", script)
        self.assertIn('/api/v1/social/feed/?_pulso=', script)
        self.assertIn('/api/v1/auth/me/?_pulso=', script)
        self.assertIn('cache: "no-store"', script)
        self.assertIn("renderFeed(feed, me", script)
        self.assertIn("pageContent.innerHTML", script)
        self.assertIn("data-pulso-retry", script)
        self.assertIn("requestTimeoutMs = 10000", script)
        self.assertIn("stallDelayMs = 3500", script)
        self.assertNotIn("window.location.reload()", script)
        self.assertNotIn("sessionStorage", script)
        self.assertNotIn("window.fetch =", script)

    def test_feed_watchdog_never_replays_mutating_requests(self):
        script = Path(settings.BASE_DIR, "static", "webapp", "lifecycle-recovery.js").read_text(encoding="utf-8")

        self.assertIn('method: "GET"', script)
        self.assertNotIn('method: "POST"', script)
        self.assertNotIn('method: "PATCH"', script)
        self.assertNotIn('method: "DELETE"', script)
