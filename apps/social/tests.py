from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Follow

from .models import Bookmark, Comment, Like, Post, Repost

User = get_user_model()


class SocialAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="kai", email="kai@test.dev", password="VeryStrong!123")
        self.followed = User.objects.create_user(username="maia", email="maia@test.dev", password="VeryStrong!123")
        self.stranger = User.objects.create_user(username="noa", email="noa@test.dev", password="VeryStrong!123")
        self.own_post = Post.objects.create(author=self.user, body="Meu processo", category="art")
        self.followed_post = Post.objects.create(author=self.followed, body="Novo ensaio", category="photography")
        self.stranger_post = Post.objects.create(author=self.stranger, body="Uma obra", category="art")
        self.client.force_authenticate(self.user)

    def test_post_creation_and_expected_fields(self):
        response = self.client.post("/api/v1/social/posts/", {"body": "Trabalho novo", "category": "design", "tags": "Design, processo,design"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["author"]["username"], "kai")
        self.assertEqual(response.data["tag_list"], ["design", "processo"])
        self.assertIn("likes_count", response.data)

    def test_blank_post_is_rejected(self):
        response = self.client.post("/api/v1/social/posts/", {"body": "", "category": "art"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_over_500_characters_is_rejected(self):
        response = self.client.post("/api/v1/social/posts/", {"body": "x" * 501, "category": "art"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_user_cannot_modify_another_users_post(self):
        response = self.client.patch(f"/api/v1/social/posts/{self.followed_post.pk}/", {"body": "hack"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_feed_contains_only_followed_people(self):
        Follow.objects.create(follower=self.user, following=self.followed)
        response = self.client.get(reverse("feed"))
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(self.followed_post.pk, ids)
        self.assertNotIn(self.stranger_post.pk, ids)
        self.assertNotIn(self.own_post.pk, ids)

    def test_like_bookmark_and_repost_toggle(self):
        for action, model in (("like", Like), ("bookmark", Bookmark), ("repost", Repost)):
            response = self.client.post(f"/api/v1/social/posts/{self.followed_post.pk}/{action}/")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(model.objects.filter(user=self.user, post=self.followed_post).exists())
            self.client.post(f"/api/v1/social/posts/{self.followed_post.pk}/{action}/")
            self.assertFalse(model.objects.filter(user=self.user, post=self.followed_post).exists())

    def test_comment_is_created_for_post(self):
        response = self.client.post(f"/api/v1/social/posts/{self.followed_post.pk}/comments/", {"body": "Que trabalho lindo!"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Comment.objects.filter(author=self.user, post=self.followed_post).exists())

    def test_unauthenticated_request_is_rejected(self):
        self.client.force_authenticate(None)
        response = self.client.get(reverse("feed"))
        self.assertIn(response.status_code, (401, 403))
