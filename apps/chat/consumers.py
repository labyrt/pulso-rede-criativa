from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone
from collections import deque
from time import monotonic

from apps.social.models import Notification

from .models import Conversation, Message


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"conversation_{self.conversation_id}"
        user = self.scope["user"]
        if not user.is_authenticated or not await self._is_participant(user.id):
            await self.close(code=4403)
            return
        self.message_times = deque()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event_type = content.get("type")
        if event_type == "message":
            now = monotonic()
            while self.message_times and now - self.message_times[0] > 60:
                self.message_times.popleft()
            if len(self.message_times) >= 30:
                await self.send_json({"type": "error", "message": "Muitas mensagens em pouco tempo. Respire e tente novamente."})
                return
            self.message_times.append(now)
            body = str(content.get("body", "")).strip()
            if not body or len(body) > 2000:
                await self.send_json({"type": "error", "message": "Mensagem inválida."})
                return
            message = await self._save_message(self.scope["user"].id, body)
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "chat.message", "message": message},
            )
        elif event_type == "signal":
            signal = content.get("signal", {})
            if not isinstance(signal, dict) or len(str(signal)) > 50000:
                return
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "rtc.signal",
                    "sender_id": self.scope["user"].id,
                    "signal": signal,
                },
            )
        elif event_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing.event",
                    "sender_id": self.scope["user"].id,
                    "active": bool(content.get("active")),
                },
            )

    async def chat_message(self, event):
        await self.send_json({"type": "message", "message": event["message"]})

    async def rtc_signal(self, event):
        if event["sender_id"] != self.scope["user"].id:
            await self.send_json({"type": "signal", "signal": event["signal"]})

    async def typing_event(self, event):
        if event["sender_id"] != self.scope["user"].id:
            await self.send_json({"type": "typing", "active": event["active"]})

    @database_sync_to_async
    def _is_participant(self, user_id):
        return Conversation.objects.filter(pk=self.conversation_id, participants__pk=user_id).exists()

    @database_sync_to_async
    def _save_message(self, user_id, body):
        conversation = Conversation.objects.get(pk=self.conversation_id)
        message = Message(conversation=conversation, sender_id=user_id)
        message.set_body(body)
        message.save()
        Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
        sender = message.sender
        for recipient in conversation.participants.exclude(pk=user_id):
            Notification.objects.create(recipient=recipient, actor=sender, kind=Notification.Kind.MESSAGE)
        return {
            "id": message.pk,
            "body": message.body,
            "sender": {"id": sender.pk, "username": sender.username, "display_name": sender.profile.name},
            "created_at": message.created_at.isoformat(),
        }
