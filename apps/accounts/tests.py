from io import BytesIO
import tempfile

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
        self.assertEqual(self.user.profile.cover_position_y, 50)
        self.assertFalse(self.user.profile.is_hidden)

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

    def test_cover_position_can_be_adjusted(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(reverse("me"), {"cover_position_y": 18}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cover_position_y"], 18)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.cover_position_y, 18)

    def test_cover_position_rejects_out_of_range_value(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(reverse("me"), {"cover_position_y": 101}, format="json")
        self.assertEqual(response.status_code, 400)

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

    def test_connections_endpoints_list_followers_and_following(self):
        third = User.objects.create_user(username="ceu", email="ceu@test.dev", password="VeryStrong!123")
        Follow.objects.create(follower=self.user, following=self.other)
        Follow.objects.create(follower=third, following=self.user)
        self.client.force_authenticate(self.user)

        following = self.client.get(reverse("connections", kwargs={"username": self.user.username, "kind": "following"}))
        followers = self.client.get(reverse("connections", kwargs={"username": self.user.username, "kind": "followers"}))

        self.assertEqual(following.status_code, 200)
        self.assertEqual([item["username"] for item in following.data["results"]], ["sol"])
        self.assertEqual(followers.status_code, 200)
        self.assertEqual([item["username"] for item in followers.data["results"]], ["ceu"])

    def test_hidden_profile_is_private_and_removed_from_connections(self):
        hidden = User.objects.create_user(username="labyrt-adm", email="admin@test.dev", password="VeryStrong!123")
        hidden.profile.is_hidden = True
        hidden.profile.save(update_fields=["is_hidden", "updated_at"])
        Follow.objects.create(follower=hidden, following=self.other)

        self.client.force_authenticate(self.user)
        hidden_profile = self.client.get(reverse("profile", kwargs={"username": hidden.username}))
        followers = self.client.get(reverse("connections", kwargs={"username": self.other.username, "kind": "followers"}))
        creators = self.client.get(reverse("creators"))

        self.assertEqual(hidden_profile.status_code, 404)
        self.assertNotIn("labyrt-adm", [item["username"] for item in followers.data["results"]])
        self.assertNotIn("labyrt-adm", [item["username"] for item in creators.data["results"]])

        self.client.force_authenticate(hidden)
        own_profile = self.client.get(reverse("profile", kwargs={"username": hidden.username}))
        self.assertEqual(own_profile.status_code, 200)
        self.assertEqual(own_profile.data["username"], "labyrt-adm")

    def test_hidden_profile_cannot_be_followed_by_username(self):
        self.other.profile.is_hidden = True
        self.other.profile.save(update_fields=["is_hidden", "updated_at"])
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("follow", kwargs={"username": self.other.username}))
        self.assertEqual(response.status_code, 404)

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
