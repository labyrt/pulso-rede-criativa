from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.serializers import ProfileUpdateSerializer, PublicProfileSerializer


User = get_user_model()


class RandomPixProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pixcreator",
            email="pixcreator@example.com",
            password="VeryStrong!123",
        )
        self.profile = self.user.profile
        self.random_key = "123e4567-e89b-12d3-a456-426655440000"

    def test_accepts_random_pix_key_and_forces_random_type(self):
        serializer = ProfileUpdateSerializer(
            self.profile,
            data={
                "pix_key": self.random_key.upper(),
                "pix_receiver_name": "Criadora PULSO",
                "pix_city": "SAO PAULO",
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        profile = serializer.save()
        self.assertEqual(profile.pix_key_type, "random")
        self.assertEqual(profile.pix_key, self.random_key)

    def test_rejects_non_random_key_type(self):
        serializer = ProfileUpdateSerializer(
            self.profile,
            data={"pix_key_type": "email"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("pix_key_type", serializer.errors)

    def test_rejects_personal_identifier_pix_keys(self):
        for value in ("criadora@example.com", "+5511999999999", "12345678901"):
            with self.subTest(value=value):
                serializer = ProfileUpdateSerializer(
                    self.profile,
                    data={"pix_key": value},
                    partial=True,
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn("pix_key", serializer.errors)

    def test_clearing_pix_key_also_clears_type(self):
        self.profile.pix_key_type = "random"
        self.profile.set_pix_key(self.random_key)
        self.profile.save(update_fields=["pix_key_type", "pix_key_ciphertext", "updated_at"])

        serializer = ProfileUpdateSerializer(
            self.profile,
            data={"pix_key": ""},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        profile = serializer.save()
        self.assertEqual(profile.pix_key_type, "")
        self.assertEqual(profile.pix_key, "")

    def test_public_support_is_enabled_only_for_random_key(self):
        self.profile.set_pix_key(self.random_key)
        self.profile.pix_receiver_name = "Criadora PULSO"
        self.profile.pix_city = "SAO PAULO"
        self.profile.pix_key_type = "email"
        self.profile.save()

        legacy_data = PublicProfileSerializer(self.profile).data
        self.assertFalse(legacy_data["pix_enabled"])

        self.profile.pix_key_type = "random"
        self.profile.save(update_fields=["pix_key_type", "updated_at"])
        random_data = PublicProfileSerializer(self.profile).data
        self.assertTrue(random_data["pix_enabled"])
