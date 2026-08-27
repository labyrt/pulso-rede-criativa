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

    def test_lifecycle_recovery_handles_bfcache_and_stalled_cold_start_without_monkeypatching_fetch(self):
        script = Path(settings.BASE_DIR, "static", "webapp", "lifecycle-recovery.js").read_text(encoding="utf-8")

        self.assertIn('window.addEventListener("pageshow"', script)
        self.assertIn("event.persisted", script)
        self.assertIn("new AbortController()", script)
        self.assertIn("/health/?_pulso=", script)
        self.assertIn('cache: "no-store"', script)
        self.assertIn("window.location.reload()", script)
        self.assertIn("sessionStorage", script)
        self.assertIn("reloadWindowMs = 120000", script)
        self.assertIn("healthTimeoutMs = 12000", script)
        self.assertIn("maxHealthAttempts = 2", script)
        self.assertIn("healthAttempts >= maxHealthAttempts", script)
        self.assertIn("showRetryState();", script)
        self.assertIn("banco de dados ainda está acordando", script)
        self.assertIn('if (section === "feed") armRecovery();', script)
        self.assertNotIn("window.fetch =", script)
