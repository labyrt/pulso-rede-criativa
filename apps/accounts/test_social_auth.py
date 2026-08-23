from types import SimpleNamespace
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from .adapters import PulsoSocialAccountAdapter


User = get_user_model()


class SocialLoginBridgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="luna", email="luna@test.dev", is_active=True)

    def _sociallogin(self, provider, verified=True):
        sociallogin = Mock()
        sociallogin.is_existing = False
        sociallogin.account.provider = provider
        sociallogin.email_addresses = [SimpleNamespace(email=self.user.email, verified=verified)]
        return sociallogin

    def test_verified_github_email_reuses_existing_account(self):
        sociallogin = self._sociallogin("github")

        PulsoSocialAccountAdapter().pre_social_login(Mock(), sociallogin)

        sociallogin.connect.assert_called_once()
        self.assertEqual(sociallogin.connect.call_args.args[1], self.user)

    def test_verified_google_email_reuses_existing_account(self):
        sociallogin = self._sociallogin("google")

        PulsoSocialAccountAdapter().pre_social_login(Mock(), sociallogin)

        sociallogin.connect.assert_called_once()
        self.assertEqual(sociallogin.connect.call_args.args[1], self.user)

    def test_unverified_trusted_email_is_not_linked(self):
        for provider in ("github", "google"):
            with self.subTest(provider=provider):
                sociallogin = self._sociallogin(provider, verified=False)

                PulsoSocialAccountAdapter().pre_social_login(Mock(), sociallogin)

                sociallogin.connect.assert_not_called()

    def test_untrusted_provider_is_not_auto_linked(self):
        sociallogin = self._sociallogin("instagram")

        PulsoSocialAccountAdapter().pre_social_login(Mock(), sociallogin)

        sociallogin.connect.assert_not_called()
