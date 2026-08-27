import os
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import TestCase, override_settings

from apps.webapp.database_guard import validate_database_target


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
            with patch("config.urls.connection.close") as close_connection:
                response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "degraded", "service": "pulso", "database": "unavailable"})
        self.assertEqual(response.headers["Retry-After"], "3")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        close_connection.assert_called_once()

    def test_neon_database_settings_bound_connection_lifetime_and_connect_wait(self):
        source = Path(settings.BASE_DIR, "config", "settings.py").read_text(encoding="utf-8")

        self.assertIn('"30" if IS_NEON_DATABASE else "600"', source)
        self.assertIn('DB_CONNECT_TIMEOUT", "10"', source)
        self.assertIn('database_options.setdefault("connect_timeout", DATABASE_CONNECT_TIMEOUT)', source)
        self.assertIn('database_options.setdefault("sslmode", "require")', source)
        self.assertIn('conn_health_checks=True', source)

    def test_health_endpoint_rejects_database_target_drift_before_connecting(self):
        env = {
            "PULSO_REQUIRE_NEON_DATABASE": "1",
            "PULSO_EXPECTED_DATABASE_NAME": "pulso",
            "DATABASE_URL": "postgresql://user:secret@legacy.example.com/pulso",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("config.urls.connection.cursor") as cursor:
                response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "degraded", "service": "pulso", "database": "unexpected_target"},
        )
        cursor.assert_not_called()

    @override_settings(REDIS_URL="rediss://redis.example.invalid:6379")
    def test_health_endpoint_fails_closed_when_redis_is_unavailable(self):
        with patch("config.urls.cache.get", side_effect=ConnectionError("redis unavailable")):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "degraded", "service": "pulso", "database": "ok", "redis": "unavailable"},
        )
        self.assertEqual(response.headers["Retry-After"], "3")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    @override_settings(REDIS_URL="rediss://redis.example.invalid:6379")
    def test_health_endpoint_reports_redis_ready(self):
        with patch("config.urls.cache.get", return_value=None):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redis"], "ok")

    def test_database_guard_accepts_expected_neon_target(self):
        target = validate_database_target(
            "postgresql://user:secret@ep-example.us-east-2.aws.neon.tech/pulso?sslmode=require",
            require_neon=True,
            expected_database="pulso",
        )
        self.assertEqual(target, {"provider": "neon", "database": "pulso"})

    def test_database_guard_rejects_legacy_provider(self):
        with self.assertRaises(ValueError):
            validate_database_target(
                "postgresql://user:secret@legacy.example.com/pulso",
                require_neon=True,
                expected_database="pulso",
            )

    def test_management_command_rejects_legacy_database_before_connecting(self):
        env = {
            "PULSO_REQUIRE_NEON_DATABASE": "1",
            "PULSO_EXPECTED_DATABASE_NAME": "pulso",
            "DATABASE_URL": "postgresql://user:secret@legacy.example.com/pulso",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("apps.webapp.management.commands.check_database_target.connection.cursor") as cursor:
                with self.assertRaises(CommandError):
                    call_command("check_database_target", stdout=StringIO())

        cursor.assert_not_called()
