from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import Follow, User
from apps.chat.models import CallSession, Message
from apps.common.realtime import publish_user_event
from apps.social.models import Notification, Post


def _actor_payload(user):
    profile = user.profile
    return {
        "id": user.pk,
        "username": user.username,
        "display_name": profile.name,
        "avatar_url": profile.avatar_url or "",
    }


def _notification_payload(notification):
    actor = notification.actor
    post = notification.post
    url = "/notificacoes/"
    if notification.kind == Notification.Kind.FOLLOW:
        url = f"/perfil/{actor.username}/"
    elif notification.kind == Notification.Kind.MESSAGE:
        url = "/mensagens/"
    elif post:
        url = f"/app/?post={post.pk}"
    return {
        "id": notification.pk,
        "kind": notification.kind,
        "actor": _actor_payload(actor),
        "post_id": post.pk if post else None,
        "post_excerpt": post.body[:80] if post else "",
        "created_at": notification.created_at.isoformat(),
        "url": url,
    }


@receiver(post_save, sender=Notification)
def broadcast_notification(sender, instance, created, **kwargs):
    if not created or instance.kind in {Notification.Kind.MESSAGE, Notification.Kind.CALL}:
        return
    payload = _notification_payload(instance)
    transaction.on_commit(
        lambda recipient_id=instance.recipient_id, data=payload: publish_user_event(
            recipient_id, "notification", data
        )
    )


@receiver(post_save, sender=Post)
def notify_followers_about_post(sender, instance, created, **kwargs):
    if not created or not instance.is_published:
        return
    author = instance.author
    if author.is_staff or author.is_superuser or author.profile.is_hidden:
        return

    def after_commit():
        follower_ids = list(
            Follow.objects.filter(following_id=author.pk).values_list("follower_id", flat=True)
        )
        if not follower_ids:
            return
        notifications = [
            Notification(
                recipient_id=recipient_id,
                actor_id=author.pk,
                kind=Notification.Kind.POST,
                post_id=instance.pk,
            )
            for recipient_id in follower_ids
        ]
        Notification.objects.bulk_create(notifications)
        actor = User.objects.select_related("profile").get(pk=author.pk)
        payload = {
            "kind": Notification.Kind.POST,
            "actor": _actor_payload(actor),
            "post_id": instance.pk,
            "post_excerpt": instance.body[:80],
            "created_at": instance.created_at.isoformat(),
            "url": f"/app/?post={instance.pk}",
        }
        for recipient_id in follower_ids:
            publish_user_event(recipient_id, "notification", payload)

    transaction.on_commit(after_commit)


@receiver(post_save, sender=Message)
def broadcast_message(sender, instance, created, **kwargs):
    if not created:
        return

    def after_commit():
        message = Message.objects.select_related("sender", "sender__profile", "conversation").get(pk=instance.pk)
        recipient_ids = list(
            message.conversation.participants.exclude(pk=message.sender_id).values_list("pk", flat=True)
        )
        payload = {
            "conversation_id": message.conversation_id,
            "actor": _actor_payload(message.sender),
            "created_at": message.created_at.isoformat(),
            "url": "/mensagens/",
        }
        for recipient_id in recipient_ids:
            publish_user_event(recipient_id, "message", payload)

    transaction.on_commit(after_commit)


@receiver(post_save, sender=CallSession)
def persist_incoming_call_activity(sender, instance, created, **kwargs):
    """Persist call activity; the live ringing event is emitted with the first WebRTC offer."""
    if not created:
        return

    def after_commit():
        call = CallSession.objects.select_related("conversation").get(pk=instance.pk)
        recipient_ids = list(
            call.conversation.participants.exclude(pk=call.caller_id).values_list("pk", flat=True)
        )
        if not recipient_ids:
            return
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient_id=recipient_id,
                    actor_id=call.caller_id,
                    kind=Notification.Kind.CALL,
                )
                for recipient_id in recipient_ids
            ]
        )

    transaction.on_commit(after_commit)
