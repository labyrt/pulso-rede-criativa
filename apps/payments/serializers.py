from rest_framework import serializers

from .models import SupportIntent


class SupportIntentSerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source="creator.username", read_only=True)

    class Meta:
        model = SupportIntent
        fields = ("id", "creator_username", "amount", "message", "created_at")
        read_only_fields = ("creator_username", "created_at")

    def validate_amount(self, value):
        if value is not None and (value <= 0 or value > 100000):
            raise serializers.ValidationError("Informe um valor entre R$ 0,01 e R$ 100.000,00.")
        return value
