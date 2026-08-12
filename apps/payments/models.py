from django.conf import settings
from django.db import models


class SupportIntent(models.Model):
    """A non-financial audit event: PULSO never handles or confirms the transfer."""

    supporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="support_intents",
        null=True,
        blank=True,
    )
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_received")
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    message = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
