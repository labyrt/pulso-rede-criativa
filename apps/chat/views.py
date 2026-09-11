from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Block, User

from .models import CallSession, Conversation, Message
from .serializers import CallSessionSerializer, ConversationSerializer, MessageSerializer
from .services import (
    CallStateError,
    ChatPolicyError,
    conversation_has_block,
    create_call,
    create_message,
    expire_stale_calls,
    transition_call_status,
)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        latest_message = Message.objects.select_related("sender", "sender__profile").order_by("-created_at")[:1]
        return (
            Conversation.objects.filter(participants=self.request.user)
            .annotate(
                _unread_count=Count(
                    "messages",
                    filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=self.request.user),
                    distinct=True,
                )
            )
            .prefetch_related(
                "participants",
                "participants__profile",
                Prefetch("messages", queryset=latest_message, to_attr="_latest_message"),
            )
        )

    def create(self, request, *args, **kwargs):
        username = request.data.get("username", "").strip().lower()
        target = get_object_or_404(
            User.objects.select_related("profile"),
            username=username,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            profile__is_hidden=False,
        )
        if target == request.user:
            return Response({"detail": "Escolha outra pessoa."}, status=status.HTTP_400_BAD_REQUEST)
        if Block.objects.filter(blocker__in=[request.user, target], blocked__in=[request.user, target]).exists():
            return Response({"detail": "Conversa indisponível."}, status=status.HTTP_403_FORBIDDEN)
        candidate = Conversation.objects.filter(participants=request.user).filter(participants=target).distinct().first()
        if candidate:
            conversation = candidate
            created = False
        else:
            conversation = Conversation.objects.create(created_by=request.user)
            conversation.participants.add(request.user, target)
            created = True
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @staticmethod
    def _message_limit(request):
        try:
            requested = int(request.query_params.get("limit", 60))
        except (TypeError, ValueError):
            requested = 60
        return max(20, min(requested, 100))

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if request.method == "GET":
            conversation.messages.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())
            limit = self._message_limit(request)
            messages = conversation.messages.select_related("sender", "sender__profile").order_by("-created_at")
            before = request.query_params.get("before")
            if before:
                try:
                    messages = messages.filter(pk__lt=int(before))
                except (TypeError, ValueError):
                    return Response({"detail": "Referência de mensagem inválida."}, status=status.HTTP_400_BAD_REQUEST)
            chunk = list(messages[: limit + 1])
            has_more = len(chunk) > limit
            chunk = chunk[:limit]
            chunk.reverse()
            response = Response(MessageSerializer(chunk, many=True, context={"request": request}).data)
            response["X-Has-More"] = "1" if has_more else "0"
            if chunk:
                response["X-Oldest-Message"] = str(chunk[0].pk)
            return response

        serializer = MessageSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            message = create_message(
                conversation_id=conversation.pk,
                sender_id=request.user.pk,
                body=serializer.validated_data["body"],
            )
        except ChatPolicyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(MessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def calls(self, request, pk=None):
        conversation = self.get_object()
        serializer = CallSessionSerializer(data={**request.data, "conversation": conversation.pk})
        serializer.is_valid(raise_exception=True)
        try:
            call = create_call(
                conversation_id=conversation.pk,
                caller_id=request.user.pk,
                kind=serializer.validated_data["kind"],
            )
        except ChatPolicyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except CallStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(CallSessionSerializer(call, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CallViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CallSessionSerializer

    def get_queryset(self):
        queryset = CallSession.objects.filter(conversation__participants=self.request.user)
        expire_stale_calls(queryset)
        return queryset.select_related("caller", "caller__profile").distinct()

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        call = self.get_object()
        new_status = request.data.get("status")
        client_allowed = {
            CallSession.Status.ACTIVE,
            CallSession.Status.ENDED,
            CallSession.Status.DECLINED,
        }
        if new_status not in client_allowed:
            return Response({"detail": "Status inválido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            call = transition_call_status(call_id=call.pk, user_id=request.user.pk, new_status=new_status)
        except ChatPolicyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except CallStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(CallSessionSerializer(call, context={"request": request}).data)


class IceServerView(viewsets.ViewSet):
    def list(self, request):
        servers = [{"urls": settings.WEBRTC_STUN_URL}]
        turn_ready = bool(
            settings.WEBRTC_TURN_URL
            and settings.WEBRTC_TURN_USERNAME
            and settings.WEBRTC_TURN_CREDENTIAL
        )
        if turn_ready:
            servers.append(
                {
                    "urls": settings.WEBRTC_TURN_URL,
                    "username": settings.WEBRTC_TURN_USERNAME,
                    "credential": settings.WEBRTC_TURN_CREDENTIAL,
                }
            )
        return Response({"iceServers": servers, "turnAvailable": turn_ready})
