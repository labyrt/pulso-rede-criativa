from django.conf import settings
from django.db import models

from apps.common.crypto import decrypt_text, encrypt_text


class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def includes(self, user):
        return self.participants.filter(pk=user.pk).exists()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_sent")
    ciphertext = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "-created_at"], name="chat_conv_recent_idx"),
            models.Index(fields=["conversation", "read_at"], name="chat_conv_read_idx"),
        ]

    @property
    def body(self):
        return decrypt_text(self.ciphertext)

    def set_body(self, value):
        self.ciphertext = encrypt_text(value)


class CallSession(models.Model):
    class Kind(models.TextChoices):
        AUDIO = "audio", "Áudio"
        VIDEO = "video", "Vídeo"

    class Status(models.TextChoices):
        RINGING = "ringing", "Chamando"
        ACTIVE = "active", "Em andamento"
        ENDED = "ended", "Finalizada"
        DECLINED = "declined", "Recusada"
        MISSED = "missed", "Não atendida"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="calls")
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calls_made")
    kind = models.CharField(max_length=8, choices=Kind.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RINGING)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
