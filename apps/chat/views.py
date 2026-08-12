from django.conf import settings
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Block, User
from apps.social.models import Notification

from .models import CallSession, Conversation, Message
from .serializers import CallSessionSerializer, ConversationSerializer, MessageSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).prefetch_related("participants", "participants__profile")

    def create(self, request, *args, **kwargs):
        username = request.data.get("username", "").strip().lower()
        target = get_object_or_404(User, username=username, is_active=True)
        if target == request.user:
            return Response({"detail": "Escolha outra pessoa."}, status=status.HTTP_400_BAD_REQUEST)
        if Block.objects.filter(blocker__in=[request.user, target], blocked__in=[request.user, target]).exists():
            return Response({"detail": "Conversa indisponível."}, status=status.HTTP_403_FORBIDDEN)
        candidate = (
            Conversation.objects.filter(participants=request.user)
            .filter(participants=target)
            .distinct()
            .first()
        )
        if candidate:
            conversation = candidate
            created = False
        else:
            conversation = Conversation.objects.create(created_by=request.user)
            conversation.participants.add(request.user, target)
            created = True
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if request.method == "GET":
            conversation.messages.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())
            messages = conversation.messages.select_related("sender", "sender__profile")[:200]
            return Response(MessageSerializer(messages, many=True, context={"request": request}).data)
        serializer = MessageSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(conversation=conversation, sender=request.user)
        conversation.save(update_fields=["updated_at"])
        for recipient in conversation.participants.exclude(pk=request.user.pk):
            Notification.objects.create(recipient=recipient, actor=request.user, kind=Notification.Kind.MESSAGE)
        return Response(MessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def calls(self, request, pk=None):
        conversation = self.get_object()
        serializer = CallSessionSerializer(data={**request.data, "conversation": conversation.pk})
        serializer.is_valid(raise_exception=True)
        call = serializer.save(conversation=conversation, caller=request.user)
        return Response(CallSessionSerializer(call, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CallViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CallSessionSerializer

    def get_queryset(self):
        return CallSession.objects.filter(conversation__participants=self.request.user).select_related("caller", "caller__profile")

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        call = self.get_object()
        new_status = request.data.get("status")
        allowed = {choice for choice, _ in CallSession.Status.choices}
        if new_status not in allowed:
            return Response({"detail": "Status inválido."}, status=status.HTTP_400_BAD_REQUEST)
        call.status = new_status
        if new_status in {CallSession.Status.ENDED, CallSession.Status.DECLINED, CallSession.Status.MISSED}:
            call.ended_at = timezone.now()
        call.save(update_fields=["status", "ended_at"])
        return Response(CallSessionSerializer(call, context={"request": request}).data)


class IceServerView(viewsets.ViewSet):
    def list(self, request):
        servers = [{"urls": settings.WEBRTC_STUN_URL}]
        if settings.WEBRTC_TURN_URL:
            servers.append(
                {
                    "urls": settings.WEBRTC_TURN_URL,
                    "username": settings.WEBRTC_TURN_USERNAME,
                    "credential": settings.WEBRTC_TURN_CREDENTIAL,
                }
            )
        return Response({"iceServers": servers})
