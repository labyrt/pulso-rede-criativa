from django.test import TestCase, override_settings


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class AuthenticationPageTests(TestCase):
    def test_unconfigured_social_login_options_are_not_rendered(self):
        response = self.client.get("/entrar/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "ou continue com")
        self.assertNotContains(response, "social-login-button")

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
