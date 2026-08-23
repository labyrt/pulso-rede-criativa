import os
from unittest.mock import patch

from django.db import DatabaseError
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

    def test_maintenance_mode_blocks_normal_requests_without_cache(self):
        with patch.dict(os.environ, {"PULSO_MAINTENANCE_MODE": "1"}):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "120")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex")
        self.assertIn("Content-Security-Policy", response.headers)

    def test_health_endpoint_remains_available_during_maintenance(self):
        with patch.dict(os.environ, {"PULSO_MAINTENANCE_MODE": "1"}):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "ok")

    def test_health_endpoint_fails_closed_when_database_is_unavailable(self):
        with patch("config.urls.connection.cursor", side_effect=DatabaseError("database unavailable")):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "degraded", "service": "pulso", "database": "unavailable"})

    @override_settings(REDIS_URL="rediss://redis.example.invalid:6379")
    def test_health_endpoint_fails_closed_when_redis_is_unavailable(self):
        with patch("config.urls.cache.get", side_effect=ConnectionError("redis unavailable")):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "degraded", "service": "pulso", "database": "ok", "redis": "unavailable"},
        )

    @override_settings(REDIS_URL="rediss://redis.example.invalid:6379")
    def test_health_endpoint_reports_redis_ready(self):
        with patch("config.urls.cache.get", return_value=None):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redis"], "ok")
