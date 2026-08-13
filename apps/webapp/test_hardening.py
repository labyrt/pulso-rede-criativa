from django.test import TestCase, override_settings


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class ProductionHardeningTests(TestCase):
    def test_auth_page_loads_isolated_polish_assets(self):
        response = self.client.get("/entrar/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "webapp/hardening.css")
        self.assertContains(response, "webapp/hardening.js")

    def test_csp_allows_oauth_destinations_without_open_form_policy(self):
        response = self.client.get("/entrar/")
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("form-action 'self'", policy)
        self.assertIn("https://github.com", policy)
        self.assertIn("https://accounts.google.com", policy)
        self.assertIn("https://www.linkedin.com", policy)
        self.assertIn("https://api.instagram.com", policy)
        self.assertIn("https://ims-na1.adobelogin.com", policy)
        self.assertNotIn("form-action *", policy)

    def test_landing_hero_has_no_floating_connection_or_support_overlays(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "NOVA CONEXÃO")
        self.assertNotContains(response, "APOIO RECEBIDO")
        self.assertContains(response, "Seu trabalho")
