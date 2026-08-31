from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.models import Message
from apps.social.models import Notification


_ACTIVITY_LABELS = {
    Notification.Kind.FOLLOW: "Nova conexão",
    Notification.Kind.LIKE: "Nova curtida",
    Notification.Kind.COMMENT: "Novo comentário",
    Notification.Kind.REPOST: "Novo compartilhamento",
    Notification.Kind.POST: "Nova publicação",
    Notification.Kind.MESSAGE: "Nova mensagem",
    Notification.Kind.CALL: "Nova ligação",
}


def build_widget_summary(user):
    """Return the privacy-safe payload shared by the API and Android shell."""
    unread_messages = (
        Message.objects.filter(
            conversation__participants=user,
            read_at__isnull=True,
        )
        .exclude(sender=user)
        .count()
    )
    unread_notifications = Notification.objects.filter(
        recipient=user,
        is_read=False,
    )
    latest = unread_notifications.order_by("-created_at", "-id").first()
    missed_calls = unread_notifications.filter(kind=Notification.Kind.CALL).count()

    return {
        "messages_unread": unread_messages,
        "activity_unread": unread_notifications.count(),
        "calls_unread": missed_calls,
        "latest_activity": (
            {
                "kind": latest.kind,
                "label": _ACTIVITY_LABELS.get(latest.kind, "Nova atividade"),
                "created_at": latest.created_at,
            }
            if latest
            else None
        ),
        "links": {
            "home": "/app/",
            "messages": "/mensagens/",
            "activity": "/notificacoes/",
            "compose": "/app/?composer=1",
        },
        "generated_at": timezone.now(),
    }


class WidgetSummaryView(APIView):
    """Small, private payload for the Android home-screen widget.

    The endpoint intentionally never returns message bodies, post excerpts,
    Pix data, email addresses, usernames, or display names. The widget may be
    visible while the phone is unlocked, so its default state is privacy-first.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = Response(build_widget_summary(request.user))
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response
