from collections import deque
from time import monotonic

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db.models import Q

from apps.accounts.models import Block
from apps.common.realtime import user_group_name

from .models import CallSession


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
        try:
            call_id = int(signal.get("call_id"))
        except (TypeError, ValueError):
            return

        call_context = await self._call_context(conversation_id, call_id, self.scope["user"].pk)
        if not call_context:
            return

        # Re-announce a ringing call immediately before caller-originated signaling.
        # This makes a receiver that reconnected after the original event establish
        # the correct call_id before an offer/candidate reaches the browser.
        if call_context["sender_is_caller"]:
            incoming_payload = {
                "call_id": call_context["call_id"],
                "conversation_id": conversation_id,
                "kind": call_context["kind"],
                "actor": call_context["caller"],
                "created_at": call_context["started_at"],
                "url": "/mensagens/",
            }
            for recipient_id in call_context["recipient_ids"]:
                await self.channel_layer.group_send(
                    user_group_name(recipient_id),
                    {"type": "user.event", "event_type": "incoming_call", "payload": incoming_payload},
                )

        payload = {
            "conversation_id": conversation_id,
            "sender_id": self.scope["user"].pk,
            "signal": signal,
        }
        for recipient_id in call_context["recipient_ids"]:
            await self.channel_layer.group_send(
                user_group_name(recipient_id),
                {"type": "user.event", "event_type": "call_signal", "payload": payload},
            )

    async def user_event(self, event):
        await self.send_json({"type": event["event_type"], **event.get("payload", {})})

    @database_sync_to_async
    def _call_context(self, conversation_id, call_id, user_id):
        call = (
            CallSession.objects.select_related("caller", "caller__profile", "conversation")
            .filter(
                pk=call_id,
                conversation_id=conversation_id,
                conversation__participants__pk=user_id,
                status__in=[CallSession.Status.RINGING, CallSession.Status.ACTIVE],
            )
            .first()
        )
        if not call:
            return None
        recipient_ids = list(call.conversation.participants.exclude(pk=user_id).values_list("pk", flat=True))
        if not recipient_ids:
            return None
        blocked = Block.objects.filter(
            Q(blocker_id=user_id, blocked_id__in=recipient_ids)
            | Q(blocker_id__in=recipient_ids, blocked_id=user_id)
        ).exists()
        if blocked:
            return None
        return {
            "call_id": call.pk,
            "kind": call.kind,
            "started_at": call.started_at.isoformat(),
            "sender_is_caller": call.caller_id == user_id,
            "recipient_ids": recipient_ids,
            "caller": {
                "id": call.caller_id,
                "username": call.caller.username,
                "display_name": call.caller.profile.name,
                "avatar_url": call.caller.profile.avatar_url or "",
            },
        }
