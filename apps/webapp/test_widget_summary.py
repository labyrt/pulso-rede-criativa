from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.chat.models import Conversation, Message
from apps.social.models import Notification


User = get_user_model()


class WidgetSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(
            username="widget_viewer",
            email="viewer-widget@test.dev",
            password="VeryStrong!123",
        )
        self.sender = User.objects.create_user(
            username="widget_sender",
            email="sender-widget@test.dev",
            password="VeryStrong!123",
        )
        self.viewer.profile.display_name = "Pessoa PULSO"
        self.viewer.profile.save(update_fields=["display_name", "updated_at"])
        self.conversation = Conversation.objects.create(created_by=self.viewer)
        self.conversation.participants.add(self.viewer, self.sender)

    def create_message(self, *, sender, body, read=False):
        message = Message(conversation=self.conversation, sender=sender)
        message.set_body(body)
        if read:
            from django.utils import timezone

            message.read_at = timezone.now()
        message.save()
        return message

    def test_widget_summary_requires_authentication(self):
        response = self.client.get("/api/v1/widget/summary/")
        self.assertIn(response.status_code, (401, 403))

    def test_widget_summary_returns_private_counts_without_message_content(self):
        self.create_message(sender=self.sender, body="segredo que nunca pode aparecer no widget")
        self.create_message(sender=self.sender, body="mensagem já lida", read=True)
        self.create_message(sender=self.viewer, body="mensagem enviada por mim")
        Notification.objects.create(
            recipient=self.viewer,
            actor=self.sender,
            kind=Notification.Kind.MESSAGE,
        )
        Notification.objects.create(
            recipient=self.viewer,
            actor=self.sender,
            kind=Notification.Kind.CALL,
        )

        self.client.force_authenticate(self.viewer)
        response = self.client.get("/api/v1/widget/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["display_name"], "Pessoa PULSO")
        self.assertEqual(response.data["messages_unread"], 1)
        self.assertEqual(response.data["activity_unread"], 2)
        self.assertEqual(response.data["calls_unread"], 1)
        self.assertIn(response.data["latest_activity"]["kind"], {"message", "call"})
        self.assertEqual(response["Cache-Control"], "no-store, private")

        serialized = str(response.data).lower()
        self.assertNotIn("segredo", serialized)
        self.assertNotIn("sender-widget@test.dev", serialized)
        self.assertNotIn("widget_sender", serialized)
        self.assertNotIn("pix", serialized)

    def test_widget_links_are_internal_deep_links(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get("/api/v1/widget/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["links"],
            {
                "home": "/app/",
                "messages": "/mensagens/",
                "activity": "/notificacoes/",
                "compose": "/app/?composer=1",
            },
        )
