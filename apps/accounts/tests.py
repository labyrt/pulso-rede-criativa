from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Follow

User = get_user_model()


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

    def test_register_rejects_weak_password(self):
        response = self.client.post(reverse("register"), {"username": "weak", "email": "weak@test.dev", "password": "123", "display_name": "Weak"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_login_accepts_email(self):
        response = self.client.post(reverse("login"), {"identifier": "luna@test.dev", "password": "VeryStrong!123"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "luna")

    def test_partial_profile_update_does_not_require_other_fields(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(reverse("me"), {"display_name": "Luna Nova"}, format="json")
        self.assertEqual(response.status_code, 200)
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
