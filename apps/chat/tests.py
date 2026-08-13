from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Conversation, Message

User = get_user_model()


class ChatAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="iris", email="iris@test.dev", password="VeryStrong!123")
        self.other = User.objects.create_user(username="cleo", email="cleo@test.dev", password="VeryStrong!123")
        self.outsider = User.objects.create_user(username="leo", email="leo@test.dev", password="VeryStrong!123")
        self.conversation = Conversation.objects.create(created_by=self.user)
        self.conversation.participants.add(self.user, self.other)

    def test_message_is_encrypted_at_rest_and_decrypted_for_participant(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(f"/api/v1/chat/conversations/{self.conversation.pk}/messages/", {"body": "projeto secreto"}, format="json")
        self.assertEqual(response.status_code, 201)
        message = Message.objects.get()
        self.assertNotIn("projeto secreto", message.ciphertext)
        self.assertEqual(message.body, "projeto secreto")
        self.assertEqual(response.data["content"], "projeto secreto")

    def test_outsider_cannot_read_conversation(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get(f"/api/v1/chat/conversations/{self.conversation.pk}/messages/")
        self.assertEqual(response.status_code, 404)

    def test_starting_same_direct_conversation_reuses_it(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/v1/chat/conversations/", {"username": self.other.username}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.conversation.pk)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_conversation_identifies_both_participants_unambiguously(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/chat/conversations/")
        self.assertEqual(response.status_code, 200)
        participants = response.data["results"][0]["participants"]
        self.assertEqual(
            {participant["id"] for participant in participants},
            {self.user.pk, self.other.pk},
        )
        self.assertEqual(
            {participant["username"] for participant in participants},
            {self.user.username, self.other.username},
        )
