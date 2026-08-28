from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Follow
from apps.social.models import Post


User = get_user_model()


class FeedOrderingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(
            username="viewer_order",
            email="viewer-order@test.dev",
            password="VeryStrong!123",
        )
        self.creator = User.objects.create_user(
            username="creator_order",
            email="creator-order@test.dev",
            password="VeryStrong!123",
        )
        Follow.objects.create(follower=self.viewer, following=self.creator)
        self.client.force_authenticate(self.viewer)

    def test_feed_returns_newest_post_first(self):
        older = Post.objects.create(author=self.creator, body="publicação anterior")
        newer = Post.objects.create(author=self.creator, body="publicação mais recente")

        response = self.client.get("/api/v1/social/feed/")

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertGreaterEqual(len(ids), 2)
        self.assertEqual(ids[:2], [newer.pk, older.pk])

    def test_explore_returns_newest_post_first_even_when_older_has_more_engagement(self):
        older = Post.objects.create(author=self.creator, body="publicação antiga popular")
        newer = Post.objects.create(author=self.creator, body="publicação nova")

        response = self.client.get("/api/v1/social/explore/")

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertGreaterEqual(len(ids), 2)
        self.assertEqual(ids[:2], [newer.pk, older.pk])
