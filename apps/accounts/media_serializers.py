"""Upload-specific serializers that delegate image verification to PULSO's media layer."""

from rest_framework import serializers

from .serializers import ProfileUpdateSerializer


class ProfileMediaUpdateSerializer(ProfileUpdateSerializer):
    """Avoid duplicate image decoding before the hardened media validator runs."""

    avatar_upload = serializers.FileField(write_only=True, required=False)
    cover_upload = serializers.FileField(write_only=True, required=False)
