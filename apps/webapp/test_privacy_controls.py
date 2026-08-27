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
class PrivacyControlsWebTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="privacyviewer",
            email="privacyviewer@example.com",
            password="VeryStrong!123",
        )
        self.client.force_login(self.user)

    def test_privacy_assets_are_loaded(self):
        response = self.client.get("/app/")
        html = response.content.decode("utf-8")
        self.assertIn("webapp/privacy-controls.css", html)
        self.assertIn("webapp/privacy-controls.js", html)
        self.assertLess(html.index("webapp/product-polish.js"), html.index("webapp/privacy-controls.js"))

    def test_block_control_uses_existing_api_and_disables_peer_actions(self):
        script = Path(settings.BASE_DIR, "static", "webapp", "privacy-controls.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('/block/`', script)
        self.assertIn('data-action="message-user"', script)
        self.assertIn('[data-follow]', script)
        self.assertIn("não poderão trocar novas mensagens", script)
