from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Block, User
from apps.common.realtime import publish_user_event
from apps.social.models import Notification

from .models import CallSession, Conversation, Message


class ChatPolicyError(Exception):
    """Raised when a chat action is forbidden by product policy."""


class CallStateError(Exception):
    """Raised when a call transition is invalid or not permitted."""


def conversation_has_block(conversation, user):
    other_ids = list(conversation.participants.exclude(pk=user.pk).values_list("pk", flat=True))
    if not other_ids:
        return False
    return Block.objects.filter(
        Q(blocker=user, blocked_id__in=other_ids)
        | Q(blocker_id__in=other_ids, blocked=user)
    ).exists()


@transaction.atomic
def create_message(*, conversation_id, sender_id, body):
    """Persist one message through the same policy path for REST and WebSocket."""
    clean_body = str(body or "").strip()
    if not clean_body or len(clean_body) > 2000:
        raise ChatPolicyError("Mensagem inválida.")

    conversation = Conversation.objects.select_for_update().get(pk=conversation_id)
    if not conversation.participants.filter(pk=sender_id).exists():
        raise ChatPolicyError("Conversa indisponível.")

    sender = User.objects.select_related("profile").get(pk=sender_id)
    if conversation_has_block(conversation, sender):
        raise ChatPolicyError("Não é possível enviar mensagens enquanto houver um bloqueio.")

    message = Message(conversation=conversation, sender=sender)
    message.set_body(clean_body)
    message.save()
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())

    recipient_ids = list(conversation.participants.exclude(pk=sender_id).values_list("pk", flat=True))
    Notification.objects.bulk_create(
        [
            Notification(recipient_id=recipient_id, actor=sender, kind=Notification.Kind.MESSAGE)
            for recipient_id in recipient_ids
        ]
    )
    return message


def ring_timeout_seconds():
    try:
        return max(15, int(getattr(settings, "WEBRTC_RING_TIMEOUT_SECONDS", 45)))
    except (TypeError, ValueError):
        return 45


def _publish_call_status(call, status_value):
    participant_ids = list(call.conversation.participants.values_list("pk", flat=True))
    payload = {
        "call_id": call.pk,
        "conversation_id": call.conversation_id,
        "status": status_value,
    }
    for participant_id in participant_ids:
        publish_user_event(participant_id, "call_status", payload)


def expire_stale_calls(queryset=None):
    """Move abandoned ringing calls to MISSED so they cannot remain live forever."""
    base = queryset if queryset is not None else CallSession.objects.all()
    now = timezone.now()
    cutoff = now - timedelta(seconds=ring_timeout_seconds())
    stale = list(
        base.filter(status=CallSession.Status.RINGING, started_at__lt=cutoff)
        .select_related("conversation")
        .prefetch_related("conversation__participants")
    )
    expired = 0
    for call in stale:
        updated = CallSession.objects.filter(
            pk=call.pk,
            status=CallSession.Status.RINGING,
        ).update(
            status=CallSession.Status.MISSED,
            ended_at=now,
        )
        if not updated:
            continue
        expired += 1
        transaction.on_commit(
            lambda call=call: _publish_call_status(call, CallSession.Status.MISSED)
        )
    return expired


@transaction.atomic
def create_call(*, conversation_id, caller_id, kind):
    conversation = Conversation.objects.select_for_update().get(pk=conversation_id)
    if not conversation.participants.filter(pk=caller_id).exists():
        raise ChatPolicyError("Conversa indisponível.")

    caller = User.objects.select_related("profile").get(pk=caller_id)
    if conversation_has_block(conversation, caller):
        raise ChatPolicyError("Não é possível iniciar chamadas enquanto houver um bloqueio.")

    expire_stale_calls(CallSession.objects.filter(conversation=conversation))
    if CallSession.objects.filter(
        conversation=conversation,
        status__in=[CallSession.Status.RINGING, CallSession.Status.ACTIVE],
    ).exists():
        raise CallStateError("Já existe uma chamada em andamento nesta conversa.")

    return CallSession.objects.create(conversation=conversation, caller=caller, kind=kind)


@transaction.atomic
def transition_call_status(*, call_id, user_id, new_status):
    call = (
        CallSession.objects.select_for_update()
        .select_related("conversation", "caller")
        .get(pk=call_id)
    )
    if not call.conversation.participants.filter(pk=user_id).exists():
        raise ChatPolicyError("Chamada indisponível.")

    expire_stale_calls(CallSession.objects.filter(pk=call.pk))
    call.refresh_from_db(fields=["status", "ended_at", "started_at"])

    if call.status == new_status:
        return call

    allowed_transitions = {
        CallSession.Status.RINGING: {
            CallSession.Status.ACTIVE,
            CallSession.Status.DECLINED,
            CallSession.Status.ENDED,
            CallSession.Status.MISSED,
        },
        CallSession.Status.ACTIVE: {CallSession.Status.ENDED},
        CallSession.Status.ENDED: set(),
        CallSession.Status.DECLINED: set(),
        CallSession.Status.MISSED: set(),
    }
    if new_status not in allowed_transitions.get(call.status, set()):
        raise CallStateError("Esta chamada não pode mudar para esse estado.")

    is_caller = call.caller_id == user_id
    if is_caller and new_status in {CallSession.Status.ACTIVE, CallSession.Status.DECLINED}:
        raise CallStateError("Somente quem recebe a chamada pode atender ou recusar.")
    if new_status == CallSession.Status.MISSED:
        if not is_caller:
            raise CallStateError("Somente quem iniciou a chamada pode marcar ausência de resposta.")
        if timezone.now() < call.started_at + timedelta(seconds=ring_timeout_seconds()):
            raise CallStateError("A chamada ainda está dentro do tempo de resposta.")

    call.status = new_status
    if new_status in {CallSession.Status.ENDED, CallSession.Status.DECLINED, CallSession.Status.MISSED}:
        call.ended_at = timezone.now()
    call.save(update_fields=["status", "ended_at"])

    transaction.on_commit(lambda: _publish_call_status(call, call.status))
    return call
