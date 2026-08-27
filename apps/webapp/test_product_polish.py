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
class ProductPolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="polishviewer",
            email="polishviewer@example.com",
            password="VeryStrong!123",
        )
        self.client.force_login(self.user)

    def test_polish_assets_load_after_existing_theme_and_interaction_layers(self):
        response = self.client.get("/app/")
        html = response.content.decode("utf-8")

        self.assertIn("webapp/product-polish.css", html)
        self.assertIn("webapp/product-polish.js", html)
        self.assertLess(html.index("webapp/mobile-accessibility.css"), html.index("webapp/product-polish.css"))
        self.assertLess(html.index("webapp/profile-chat-enhancements.js"), html.index("webapp/product-polish.js"))

    def test_css_covers_mobile_profile_landing_and_dark_mode_contracts(self):
        css = Path(settings.BASE_DIR, "static", "webapp", "product-polish.css").read_text(encoding="utf-8")

        self.assertIn(".float-card--main", css)
        self.assertIn(".profile-actions", css)
        self.assertIn(".profile-support-action", css)
        self.assertIn('html[data-theme="dark"] .modal-card', css)
        self.assertIn('html[data-theme="dark"] .profile-cover', css)
        self.assertIn("background-size: 100% auto", css)
        self.assertIn("@media (max-width: 640px)", css)

    def test_client_polish_only_enhances_idempotently_and_uses_random_pix_pattern(self):
        script = Path(settings.BASE_DIR, "static", "webapp", "product-polish.js").read_text(encoding="utf-8")

        self.assertIn("RANDOM_PIX_PATTERN", script)
        self.assertIn("Somente chave aleatória (EVP)", script)
        self.assertIn("Apoiar via Pix", script)
        self.assertIn('typeSelect.closest("label")?.remove()', script)
        self.assertIn('button.dataset.supportPolished === "true"', script)
        self.assertIn("MutationObserver", script)
        self.assertIn("childList: true", script)
        self.assertNotIn("characterData: true", script)
