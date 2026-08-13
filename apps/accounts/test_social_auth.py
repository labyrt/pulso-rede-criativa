from types import SimpleNamespace
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from .adapters import PulsoSocialAccountAdapter


User = get_user_model()


class SocialLoginBridgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="luna", email="luna@test.dev", is_active=True)

    def test_verified_github_email_reuses_existing_account(self):
        sociallogin = Mock()
        sociallogin.is_existing = False
        sociallogin.account.provider = "github"
        sociallogin.email_addresses = [SimpleNamespace(email=self.user.email, verified=True)]

        PulsoSocialAccountAdapter().pre_social_login(Mock(), sociallogin)

        sociallogin.connect.assert_called_once()
        self.assertEqual(sociallogin.connect.call_args.args[1], self.user)

    def test_unverified_github_email_is_not_linked(self):
        sociallogin = Mock()
        sociallogin.is_existing = False
        sociallogin.account.provider = "github"
        sociallogin.email_addresses = [SimpleNamespace(email=self.user.email, verified=False)]

        PulsoSocialAccountAdapter().pre_social_login(Mock(), sociallogin)

        sociallogin.connect.assert_not_called()
