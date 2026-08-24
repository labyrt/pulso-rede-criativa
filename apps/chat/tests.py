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

    def create_message(self, sender, body):
        message = Message(conversation=self.conversation, sender=sender)
        message.set_body(body)
        message.save()
        return message

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

    def test_hidden_profile_cannot_be_started_by_username(self):
        self.other.profile.is_hidden = True
        self.other.profile.save(update_fields=["is_hidden", "updated_at"])
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/v1/chat/conversations/", {"username": self.other.username}, format="json")
        self.assertEqual(response.status_code, 404)

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

    def test_conversation_list_exposes_latest_message_and_unread_count(self):
        self.create_message(self.other, "primeira")
        latest = self.create_message(self.other, "mais recente")
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/chat/conversations/")

        self.assertEqual(response.status_code, 200)
        item = response.data["results"][0]
        self.assertEqual(item["last_message"]["id"], latest.pk)
        self.assertEqual(item["last_message"]["content"], "mais recente")
        self.assertEqual(item["unread_count"], 2)

    def test_messages_load_recent_chunk_and_can_fetch_older_history(self):
        created = [self.create_message(self.other, f"mensagem {index}") for index in range(65)]
        self.client.force_authenticate(self.user)

        recent = self.client.get(f"/api/v1/chat/conversations/{self.conversation.pk}/messages/")

        self.assertEqual(recent.status_code, 200)
        self.assertEqual(len(recent.data), 60)
        self.assertEqual(recent.data[0]["id"], created[5].pk)
        self.assertEqual(recent.data[-1]["id"], created[-1].pk)
        self.assertEqual(recent.headers["X-Has-More"], "1")
        self.assertEqual(recent.headers["X-Oldest-Message"], str(created[5].pk))

        older = self.client.get(
            f"/api/v1/chat/conversations/{self.conversation.pk}/messages/?before={created[5].pk}&limit=60"
        )
        self.assertEqual(older.status_code, 200)
        self.assertEqual([item["id"] for item in older.data], [message.pk for message in created[:5]])
        self.assertEqual(older.headers["X-Has-More"], "0")
