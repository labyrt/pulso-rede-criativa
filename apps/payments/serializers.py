from rest_framework import serializers

from apps.social.models import Post

from .models import SupportIntent


class SupportIntentSerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source="creator.username", read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.filter(is_published=True), required=False, allow_null=True)

    class Meta:
        model = SupportIntent
        fields = ("id", "creator_username", "post", "amount", "message", "created_at")
        read_only_fields = ("creator_username", "created_at")

    def validate_amount(self, value):
        if value is not None and (value <= 0 or value > 100000):
            raise serializers.ValidationError("Informe um valor entre R$ 0,01 e R$ 100.000,00.")
        return value

    def validate(self, attrs):
        creator = self.context.get("creator")
        post = attrs.get("post")
        if post and creator and post.author_id != creator.pk:
            raise serializers.ValidationError({"post": "Esta publicação não pertence à pessoa apoiada."})
        if post and not post.accepts_support:
            raise serializers.ValidationError({"post": "Esta publicação não está recebendo apoios."})
        return attrs
