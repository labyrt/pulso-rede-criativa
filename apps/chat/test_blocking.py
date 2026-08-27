from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Block


User = get_user_model()


class ChatBlockingTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="VeryStrong!123",
        )
        self.recipient = User.objects.create_user(
            username="recipient",
            email="recipient@example.com",
            password="VeryStrong!123",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.sender)
        response = self.client.post(
            "/api/v1/chat/conversations/",
            {"username": self.recipient.username},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.conversation_id = response.data["id"]

    def test_existing_conversation_becomes_read_only_after_block(self):
        Block.objects.create(blocker=self.sender, blocked=self.recipient)

        message = self.client.post(
            f"/api/v1/chat/conversations/{self.conversation_id}/messages/",
            {"body": "Esta mensagem não deve ser enviada."},
            format="json",
        )
        self.assertEqual(message.status_code, 403)

        call = self.client.post(
            f"/api/v1/chat/conversations/{self.conversation_id}/calls/",
            {"kind": "audio"},
            format="json",
        )
        self.assertEqual(call.status_code, 403)

        history = self.client.get(
            f"/api/v1/chat/conversations/{self.conversation_id}/messages/"
        )
        self.assertEqual(history.status_code, 200)
