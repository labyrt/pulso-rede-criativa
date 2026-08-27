from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.social.models import Post
from apps.social.serializers import PostSerializer


User = get_user_model()


class RandomPixPostSupportTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username="randomsupport",
            email="randomsupport@example.com",
            password="VeryStrong!123",
        )
        self.post = Post.objects.create(
            author=self.creator,
            body="Trabalho apoiável",
            accepts_support=True,
        )
        profile = self.creator.profile
        profile.pix_receiver_name = "RANDOM SUPPORT"
        profile.pix_city = "SAO PAULO"
        profile.set_pix_key("legacy@example.com")
        profile.pix_key_type = "email"
        profile.save()

    def test_legacy_non_random_key_does_not_enable_post_support(self):
        data = PostSerializer(self.post).data
        self.assertFalse(data["pix_enabled"])

    def test_random_key_enables_post_support(self):
        profile = self.creator.profile
        profile.set_pix_key("123e4567-e89b-12d3-a456-426655440000")
        profile.pix_key_type = "random"
        profile.save(update_fields=["pix_key_ciphertext", "pix_key_type", "updated_at"])

        data = PostSerializer(self.post).data
        self.assertTrue(data["pix_enabled"])
