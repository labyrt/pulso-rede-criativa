from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.social.models import Post

from .models import SupportIntent
from .pix import build_pix_payload

User = get_user_model()


class PixTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.creator = User.objects.create_user(username="dara", email="dara@test.dev", password="VeryStrong!123")
        self.supporter = User.objects.create_user(username="bia", email="bia@test.dev", password="VeryStrong!123")
        profile = self.creator.profile
        profile.set_pix_key("dara@test.dev")
        profile.pix_key_type = "email"
        profile.pix_receiver_name = "DARA LUZ"
        profile.pix_city = "RECIFE"
        profile.save()
        self.client.force_authenticate(self.supporter)

    def test_pix_payload_has_valid_structure_and_crc(self):
        payload = build_pix_payload("dara@test.dev", "DARA LUZ", "RECIFE", 25.0)
        self.assertTrue(payload.startswith("000201"))
        self.assertIn("BR.GOV.BCB.PIX", payload)
        self.assertRegex(payload[-4:], r"^[0-9A-F]{4}$")

    def test_pix_endpoint_returns_svg_but_not_profile_secret_field(self):
        response = self.client.get(f"/api/v1/support/{self.creator.username}/pix/?amount=25")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<svg", response.data["qr_svg"])
        self.assertNotIn("pix_key_ciphertext", response.data)

    def test_support_intent_can_reference_a_creator_post(self):
        post = Post.objects.create(author=self.creator, body="Processo apoiável", accepts_support=True)
        response = self.client.post(
            f"/api/v1/support/{self.creator.username}/intent/",
            {"post": post.pk, "message": "Apoio iniciado via QR Code"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(SupportIntent.objects.filter(creator=self.creator, supporter=self.supporter, post=post).exists())

    def test_support_intent_rejects_another_creators_post(self):
        other = User.objects.create_user(username="outra", email="outra@test.dev", password="VeryStrong!123")
        post = Post.objects.create(author=other, body="Outro trabalho")
        response = self.client.post(
            f"/api/v1/support/{self.creator.username}/intent/",
            {"post": post.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
