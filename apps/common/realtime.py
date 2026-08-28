import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


logger = logging.getLogger("pulso.realtime")


def user_group_name(user_id):
    return f"user_{int(user_id)}"


def publish_user_event(user_id, event_type, payload=None):
    """Publish a small, content-safe event without blocking the primary product action."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return False
    try:
        async_to_sync(channel_layer.group_send)(
            user_group_name(user_id),
            {
                "type": "user.event",
                "event_type": str(event_type),
                "payload": payload or {},
            },
        )
        return True
    except Exception:
        logger.warning(
            "Live event delivery failed user_id=%s event_type=%s",
            user_id,
            event_type,
            exc_info=True,
        )
        return False
