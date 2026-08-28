from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Follow
from apps.chat.models import CallSession, Conversation
from apps.social.models import Notification, Post


User = get_user_model()


class PwaDeliveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pwatester",
            email="pwa@test.dev",
            password="VeryStrong!123",
        )

    def test_manifest_is_installable_and_uses_pulso_identity(self):
        response = self.client.get("/manifest.webmanifest")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/manifest+json"))
        manifest = response.json()
        self.assertEqual(manifest["short_name"], "PULSO")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["theme_color"], "#0b0b0c")
        sizes = {icon["sizes"] for icon in manifest["icons"]}
        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)
        self.assertTrue(any(icon.get("purpose") == "maskable" for icon in manifest["icons"]))

    def test_service_worker_is_root_scoped_and_does_not_cache_api(self):
        response = self.client.get("/service-worker.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertIn("no-cache", response["Cache-Control"])
        source = response.content.decode("utf-8")
        self.assertIn('url.pathname.startsWith("/api/")', source)
        self.assertIn('request.mode === "navigate"', source)
        self.assertIn("OFFLINE_URL", source)

    def test_pwa_assets_are_present(self):
        base = Path(settings.BASE_DIR, "static", "webapp")
        for relative in (
            "service-worker.js",
            "offline.html",
            "pwa.js",
            "realtime.js",
            "pwa-realtime.css",
            "icons/pulso-192.png",
            "icons/pulso-512.png",
            "icons/pulso-maskable-512.png",
            "icons/apple-touch-icon-180.png",
        ):
            self.assertTrue((base / relative).exists(), relative)

    def test_authenticated_shell_links_manifest_and_live_scripts(self):
        self.client.force_login(self.user)
        response = self.client.get("/app/")
        html = response.content.decode("utf-8")
        self.assertIn('rel="manifest" href="/manifest.webmanifest"', html)
        self.assertIn("webapp/pwa.js", html)
        self.assertIn("webapp/realtime.js", html)
        self.assertIn("webapp/pwa-realtime.css", html)


class LiveProductSignalsTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username="creatorlive",
            email="creator@test.dev",
            password="VeryStrong!123",
        )
        self.follower = User.objects.create_user(
            username="followerlive",
            email="follower@test.dev",
            password="VeryStrong!123",
        )
        Follow.objects.create(follower=self.follower, following=self.creator)

    def test_new_post_creates_persistent_follower_activity(self):
        with self.captureOnCommitCallbacks(execute=True):
            post = Post.objects.create(author=self.creator, body="Novo processo criativo")
        notification = Notification.objects.get(
            recipient=self.follower,
            actor=self.creator,
            kind=Notification.Kind.POST,
        )
        self.assertEqual(notification.post, post)

    def test_new_call_creates_persistent_call_activity(self):
        conversation = Conversation.objects.create(created_by=self.creator)
        conversation.participants.add(self.creator, self.follower)
        with self.captureOnCommitCallbacks(execute=True):
            CallSession.objects.create(
                conversation=conversation,
                caller=self.creator,
                kind=CallSession.Kind.AUDIO,
            )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.follower,
                actor=self.creator,
                kind=Notification.Kind.CALL,
            ).exists()
        )
