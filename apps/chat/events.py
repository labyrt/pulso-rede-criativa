from collections import deque
from time import monotonic

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db.models import Q

from apps.accounts.models import Block
from apps.common.realtime import user_group_name

from .models import Conversation


class UserEventsConsumer(AsyncJsonWebsocketConsumer):
    """Always-on authenticated channel for live notifications and call signaling."""

    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        self.user_group = user_group_name(user.pk)
        self.signal_times = deque()
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") != "call.signal":
            return

        now = monotonic()
        while self.signal_times and now - self.signal_times[0] > 60:
            self.signal_times.popleft()
        if len(self.signal_times) >= 180:
            await self.send_json({"type": "error", "message": "Sinalização de chamada temporariamente limitada."})
            return
        self.signal_times.append(now)

        try:
            conversation_id = int(content.get("conversation_id"))
        except (TypeError, ValueError):
            return
        signal = content.get("signal")
        if not isinstance(signal, dict) or len(str(signal)) > 50000:
            return

        recipient_ids = await self._call_recipients(conversation_id, self.scope["user"].pk)
        if not recipient_ids:
            return
        payload = {
            "conversation_id": conversation_id,
            "sender_id": self.scope["user"].pk,
            "signal": signal,
        }
        for recipient_id in recipient_ids:
            await self.channel_layer.group_send(
                user_group_name(recipient_id),
                {"type": "user.event", "event_type": "call_signal", "payload": payload},
            )

    async def user_event(self, event):
        await self.send_json({"type": event["event_type"], **event.get("payload", {})})

    @database_sync_to_async
    def _call_recipients(self, conversation_id, user_id):
        conversation = Conversation.objects.filter(pk=conversation_id, participants__pk=user_id).first()
        if not conversation:
            return []
        recipient_ids = list(conversation.participants.exclude(pk=user_id).values_list("pk", flat=True))
        if not recipient_ids:
            return []
        blocked = Block.objects.filter(
            Q(blocker_id=user_id, blocked_id__in=recipient_ids)
            | Q(blocker_id__in=recipient_ids, blocked_id=user_id)
        ).exists()
        return [] if blocked else recipient_ids
