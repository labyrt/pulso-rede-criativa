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

    def test_app_uses_native_fetch_path_without_global_wrapper(self):
        response = self.client.get("/app/")
        html = response.content.decode("utf-8")

        self.assertIn("webapp/app.js", html)
        self.assertNotIn("webapp/resilience.js", html)
