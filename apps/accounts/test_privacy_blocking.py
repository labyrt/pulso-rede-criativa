from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Follow


User = get_user_model()


class PrivacyAndBlockingTests(TestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="VeryStrong!123",
        )
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="VeryStrong!123",
        )
        self.internal = User.objects.create_superuser(
            username="labyrt_admin",
            email="internal@example.com",
            password="VeryStrong!123",
        )
        self.internal.profile.is_hidden = False
        self.internal.profile.save(update_fields=["is_hidden", "updated_at"])
        self.client = APIClient()
        self.client.force_authenticate(self.viewer)

    def test_internal_admin_never_appears_in_public_discovery_or_profile(self):
        creators = self.client.get(reverse("creators"))
        self.assertEqual(creators.status_code, 200)
        usernames = [item["username"] for item in creators.data["results"]]
        self.assertNotIn("labyrt_admin", usernames)

        public_profile = self.client.get(
            reverse("profile", kwargs={"username": self.internal.username})
        )
        self.assertEqual(public_profile.status_code, 404)

        self.client.force_authenticate(self.internal)
        own_profile = self.client.get(
            reverse("profile", kwargs={"username": self.internal.username})
        )
        self.assertEqual(own_profile.status_code, 200)
        self.assertTrue(own_profile.data["is_own"])

    def test_block_removes_follows_and_exposes_unblock_state_only_to_blocker(self):
        Follow.objects.create(follower=self.viewer, following=self.creator)
        Follow.objects.create(follower=self.creator, following=self.viewer)

        blocked = self.client.post(
            reverse("block", kwargs={"username": self.creator.username})
        )
        self.assertEqual(blocked.status_code, 200)
        self.assertTrue(blocked.data["blocked"])
        self.assertFalse(
            Follow.objects.filter(
                follower__in=[self.viewer, self.creator],
                following__in=[self.viewer, self.creator],
            ).exists()
        )

        target_profile = self.client.get(
            reverse("profile", kwargs={"username": self.creator.username})
        )
        self.assertEqual(target_profile.status_code, 200)
        self.assertTrue(target_profile.data["is_blocked"])

        other_client = APIClient()
        other_client.force_authenticate(self.creator)
        blocker_profile = other_client.get(
            reverse("profile", kwargs={"username": self.viewer.username})
        )
        self.assertEqual(blocker_profile.status_code, 404)

        unblocked = self.client.post(
            reverse("block", kwargs={"username": self.creator.username})
        )
        self.assertEqual(unblocked.status_code, 200)
        self.assertFalse(unblocked.data["blocked"])
        target_profile = self.client.get(
            reverse("profile", kwargs={"username": self.creator.username})
        )
        self.assertFalse(target_profile.data["is_blocked"])
