from io import BytesIO
import tempfile
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from .models import Follow

User = get_user_model()


def uploaded_image(name="avatar.png"):
    buffer = BytesIO()
    Image.new("RGB", (120, 120), "#5375ff").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class AccountsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="luna", email="luna@test.dev", password="VeryStrong!123")
        self.other = User.objects.create_user(username="sol", email="sol@test.dev", password="VeryStrong!123")

    def test_profile_is_created_automatically(self):
        self.assertEqual(self.user.profile.name, "luna")

    def test_register_creates_secure_session(self):
        response = self.client.post(
            reverse("register"),
            {"username": "nova_criadora", "email": "nova@test.dev", "password": "AnotherStrong!123", "display_name": "Nova Criadora"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["display_name"], "Nova Criadora")
        self.assertNotIn("password", response.data)
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    @patch("apps.accounts.views.send_email_confirmation")
    def test_mandatory_verification_registers_without_logging_in(self, send_confirmation):
        response = self.client.post(
            reverse("register"),
            {"username": "verificar", "email": "verificar@test.dev", "password": "AnotherStrong!123", "display_name": "Verificar"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["requires_email_verification"])
        self.assertNotIn("_auth_user_id", self.client.session)
        user = User.objects.get(username="verificar")
        send_confirmation.assert_called_once()
        self.assertEqual(send_confirmation.call_args.args[1], user)

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_mandatory_verification_blocks_pending_email_until_verified(self):
        address = EmailAddress.objects.create(user=self.user, email=self.user.email, verified=False, primary=True)
        response = self.client.post(
            reverse("login"),
            {"identifier": self.user.email, "password": "VeryStrong!123"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.data["requires_email_verification"])
        self.assertNotIn("_auth_user_id", self.client.session)

        address.verified = True
        address.save(update_fields=["verified"])
        response = self.client.post(
            reverse("login"),
            {"identifier": self.user.email, "password": "VeryStrong!123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_legacy_account_without_emailaddress_keeps_access(self):
        response = self.client.post(
            reverse("login"),
            {"identifier": self.user.email, "password": "VeryStrong!123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    @patch("apps.accounts.views.send_email_confirmation")
    def test_resend_verification_is_generic_and_rate_limited_endpoint(self, send_confirmation):
        response = self.client.post(reverse("resend-verification"), {"email": self.user.email}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.user.email, response.data["detail"])
        send_confirmation.assert_called_once()

        send_confirmation.reset_mock()
        response = self.client.post(reverse("resend-verification"), {"email": "nobody@test.dev"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("nobody@test.dev", response.data["detail"])
        send_confirmation.assert_not_called()

    def test_register_rejects_weak_password(self):
        response = self.client.post(reverse("register"), {"username": "weak", "email": "weak@test.dev", "password": "123", "display_name": "Weak"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_login_accepts_email(self):
        response = self.client.post(reverse("login"), {"identifier": "luna@test.dev", "password": "VeryStrong!123"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "luna")

    def test_logout_clears_the_session(self):
        self.client.post(reverse("login"), {"identifier": "luna", "password": "VeryStrong!123"}, format="json")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 204)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_partial_profile_update_does_not_require_other_fields(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(reverse("me"), {"display_name": "Luna Nova"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user.pk)
        self.assertEqual(response.data["display_name"], "Luna Nova")

    def test_password_update_hashes_value(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(reverse("me"), {"password": "UpdatedStrong!456"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("UpdatedStrong!456"))

    def test_follow_toggle_and_self_follow_protection(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("follow", kwargs={"username": self.other.username}))
        self.assertTrue(response.data["following"])
        self.assertTrue(Follow.objects.filter(follower=self.user, following=self.other).exists())
        response = self.client.post(reverse("follow", kwargs={"username": self.other.username}))
        self.assertFalse(response.data["following"])
        response = self.client.post(reverse("follow", kwargs={"username": self.user.username}))
        self.assertEqual(response.status_code, 400)

    def test_pix_key_is_never_returned_and_is_encrypted(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            reverse("me"),
            {"pix_key_type": "email", "pix_key": "pix@test.dev", "pix_receiver_name": "LUNA", "pix_city": "SAO PAULO"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertNotEqual(self.user.profile.pix_key_ciphertext, "pix@test.dev")
        self.assertEqual(self.user.profile.pix_key, "pix@test.dev")
        self.assertNotIn("pix_key", response.data)

    def test_profile_accepts_direct_image_upload_and_social_links(self):
        self.client.force_authenticate(self.user)
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root, DEBUG=True):
            response = self.client.patch(
                reverse("me"),
                {
                    "avatar_upload": uploaded_image(),
                    "github_url": "https://github.com/luna",
                    "specialty": "development",
                },
                format="multipart",
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("/media/uploads/profiles/avatars/", response.data["avatar_url"])
        self.assertEqual(response.data["github_url"], "https://github.com/luna")
        self.assertEqual(response.data["specialty_label"], "Desenvolvimento")
