from django.test import TestCase, override_settings


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class AuthenticationPageTests(TestCase):
    def test_social_login_options_are_visible_but_inactive_without_secrets(self):
        response = self.client.get("/entrar/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Google")
        self.assertContains(response, "GitHub")
        self.assertContains(response, "LinkedIn")
        self.assertContains(response, "Instagram")
        self.assertContains(response, "Adobe / Behance")
        self.assertContains(response, "disabled", count=5)

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "github": {"APPS": [{"client_id": "public-id", "secret": "server-secret"}]}
        }
    )
    def test_configured_provider_uses_post_and_never_renders_secret(self):
        response = self.client.get("/entrar/")
        self.assertContains(response, 'action="/accounts/github/login/"')
        self.assertContains(response, 'method="post"')
        self.assertNotContains(response, "server-secret")
