from collections import deque
from time import monotonic

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Conversation
from .services import ChatPolicyError, create_message


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
                await self.send_json({"type": "error", "message": "Muitas mensagens em pouco tempo. Aguarde alguns instantes e tente novamente."})
                return
            self.message_times.append(now)
            body = str(content.get("body", "")).strip()
            if not body or len(body) > 2000:
                await self.send_json({"type": "error", "message": "Mensagem inválida."})
                return
            try:
                message = await self._save_message(self.scope["user"].id, body)
            except ChatPolicyError as exc:
                await self.send_json({"type": "error", "message": str(exc)})
                return
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "chat.message", "message": message},
            )
        elif event_type == "signal":
            # WebRTC signaling is intentionally centralized in /ws/events/.
            # Keeping a second signaling path here caused call/session races.
            await self.send_json({"type": "error", "message": "Atualize a página antes de iniciar uma ligação."})
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

    async def typing_event(self, event):
        if event["sender_id"] != self.scope["user"].id:
            await self.send_json({"type": "typing", "active": event["active"]})

    @database_sync_to_async
    def _is_participant(self, user_id):
        return Conversation.objects.filter(pk=self.conversation_id, participants__pk=user_id).exists()

    @database_sync_to_async
    def _save_message(self, user_id, body):
        message = create_message(
            conversation_id=self.conversation_id,
            sender_id=user_id,
            body=body,
        )
        sender = message.sender
        # "body" remains during the frontend compatibility window; "content"
        # is the canonical field shared with the REST serializer.
        return {
            "id": message.pk,
            "content": message.body,
            "body": message.body,
            "sender": {
                "id": sender.pk,
                "username": sender.username,
                "display_name": sender.profile.name,
            },
            "created_at": message.created_at.isoformat(),
            "read_at": None,
        }
