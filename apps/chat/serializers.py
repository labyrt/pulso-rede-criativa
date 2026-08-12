from rest_framework import serializers

from apps.accounts.serializers import UserSummarySerializer

from .models import CallSession, Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)
    body = serializers.CharField(write_only=True, max_length=2000)
    content = serializers.CharField(source="body", read_only=True)

    class Meta:
        model = Message
        fields = ("id", "sender", "body", "content", "created_at", "read_at")
        read_only_fields = ("sender", "created_at", "read_at")

    def create(self, validated_data):
        body = validated_data.pop("body")
        message = Message(**validated_data)
        message.set_body(body)
        message.save()
        return message


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSummarySerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ("id", "participants", "last_message", "unread_count", "created_at", "updated_at")

    def get_last_message(self, obj):
        message = obj.messages.select_related("sender", "sender__profile").last()
        return MessageSerializer(message, context=self.context).data if message else None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        return obj.messages.exclude(sender=request.user).filter(read_at__isnull=True).count() if request else 0


class CallSessionSerializer(serializers.ModelSerializer):
    caller = UserSummarySerializer(read_only=True)

    class Meta:
        model = CallSession
        fields = ("id", "conversation", "caller", "kind", "status", "started_at", "ended_at")
        read_only_fields = ("caller", "status", "started_at", "ended_at")
