from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.webapp.native_auth_views import _challenge_for


User = get_user_model()


@override_settings(
    SOCIALACCOUNT_PROVIDERS={
        "github": {"APPS": [{"client_id": "test-client", "secret": "test-secret"}]},
    },
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class NativeAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="native_oauth_user",
            email="native-oauth@test.dev",
            password="VeryStrong!123",
        )
        self.verifier = "A" * 43
        self.challenge = _challenge_for(self.verifier)

    def tearDown(self):
        cache.clear()

    def assert_no_store_private(self, response):
        directives = {item.strip() for item in response["Cache-Control"].split(",")}
        self.assertIn("no-store", directives)
        self.assertIn("private", directives)

    def test_start_requires_valid_enabled_provider_and_challenge(self):
        response = self.client.get(
            "/native-auth/start/github/",
            {"challenge": self.challenge},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/accounts/github/login/")
        self.assertContains(response, "/native-auth/complete/")
        self.assert_no_store_private(response)

        invalid = self.client.get("/native-auth/start/github/", {"challenge": "bad"})
        self.assertEqual(invalid.status_code, 302)
        self.assertEqual(invalid.url, "/entrar/")

        disabled = self.client.get("/native-auth/start/google/", {"challenge": self.challenge})
        self.assertEqual(disabled.status_code, 302)
        self.assertEqual(disabled.url, "/entrar/")

    def test_complete_issues_short_lived_code_only_for_authenticated_browser(self):
        handoff = "handoff-test"
        pending_key = f"pulso:native-auth:pending:{handoff}"
        cache.set(pending_key, {"challenge": self.challenge, "provider": "github"}, timeout=60)

        anonymous = self.client.get("/native-auth/complete/", {"handoff": handoff})
        self.assertEqual(anonymous.status_code, 302)
        self.assertEqual(anonymous.url, "/entrar/")

        self.client.force_login(self.user)
        response = self.client.get("/native-auth/complete/", {"handoff": handoff})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("pulso://auth/callback?"))
        self.assert_no_store_private(response)
        code = parse_qs(urlparse(response.url).query)["code"][0]
        payload = cache.get(f"pulso:native-auth:code:{code}")
        self.assertEqual(payload["user_id"], self.user.pk)
        self.assertEqual(payload["challenge"], self.challenge)
        self.assertIsNone(cache.get(pending_key))

    def test_consume_binds_code_to_device_verifier_and_prevents_replay(self):
        code = "B" * 43
        code_key = f"pulso:native-auth:code:{code}"
        cache.set(
            code_key,
            {"user_id": self.user.pk, "challenge": self.challenge},
            timeout=60,
        )

        get_attempt = self.client.get(
            "/native-auth/consume/",
            {"code": code, "verifier": self.verifier},
        )
        self.assertEqual(get_attempt.status_code, 405)
        self.assertIsNotNone(cache.get(code_key))

        wrong = self.client.post(
            "/native-auth/consume/",
            {"code": code, "verifier": "C" * 43},
        )
        self.assertEqual(wrong.status_code, 302)
        self.assertEqual(wrong.url, "/entrar/")
        self.assertIsNotNone(cache.get(code_key))

        response = self.client.post(
            "/native-auth/consume/",
            {"code": code, "verifier": self.verifier},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/app/")
        self.assert_no_store_private(response)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertIsNone(cache.get(code_key))

        replay = self.client.post(
            "/native-auth/consume/",
            {"code": code, "verifier": self.verifier},
        )
        self.assertEqual(replay.status_code, 302)
        self.assertEqual(replay.url, "/entrar/")
