from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import Follow

from .models import Bookmark, Comment, Like, Post, Repost

User = get_user_model()


class FeedProductionHardeningTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="viewer",
            email="viewer@test.dev",
            password="VeryStrong!123",
        )
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@test.dev",
            password="VeryStrong!123",
        )
        Follow.objects.create(follower=self.user, following=self.creator)
        self.client.force_authenticate(self.user)

    def test_feed_relationship_flags_and_comment_preview_keep_existing_contract(self):
        post = Post.objects.create(author=self.creator, body="Processo em andamento", category="development")
        Like.objects.create(user=self.user, post=post)
        Bookmark.objects.create(user=self.user, post=post)
        Repost.objects.create(user=self.user, post=post)
        Comment.objects.create(author=self.creator, post=post, body="Primeira atualização")

        response = self.client.get("/api/v1/social/feed/")

        self.assertEqual(response.status_code, 200)
        item = response.data["results"][0]
        self.assertTrue(item["is_liked"])
        self.assertTrue(item["is_bookmarked"])
        self.assertTrue(item["is_reposted"])
        self.assertEqual(item["latest_comments"][0]["body"], "Primeira atualização")

    def test_feed_query_count_does_not_grow_linearly_with_post_count(self):
        posts = [
            Post.objects.create(author=self.creator, body=f"Post {index}", category="development")
            for index in range(8)
        ]
        for post in posts:
            Like.objects.create(user=self.user, post=post)
            Bookmark.objects.create(user=self.user, post=post)
            Comment.objects.create(author=self.creator, post=post, body="Comentário")

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/api/v1/social/feed/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 8)
        self.assertLessEqual(
            len(queries),
            20,
            f"Feed executou {len(queries)} queries; esperado no máximo 20 para uma página.",
        )

    def test_private_api_responses_are_not_cacheable(self):
        response = self.client.get("/api/v1/social/feed/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertIn("private", response.headers.get("Cache-Control", ""))
        self.assertEqual(response.headers.get("Pragma"), "no-cache")
        self.assertIn("Cookie", response.headers.get("Vary", ""))
