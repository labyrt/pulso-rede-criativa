from django.contrib.auth import password_validation
from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework import serializers

from .models import Follow, Profile, User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(write_only=True, max_length=80)

    class Meta:
        model = User
        fields = ("username", "email", "password", "display_name")

    def validate_username(self, value):
        normalized = value.lower().strip()
        if not normalized.replace("_", "").isalnum():
            raise serializers.ValidationError("Use apenas letras, números e sublinhado.")
        return normalized

    def validate_password(self, value):
        password_validation.validate_password(value, self.instance)
        return value

    @transaction.atomic
    def create(self, validated_data):
        display_name = validated_data.pop("display_name")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        user.profile.display_name = display_name
        user.profile.save(update_fields=["display_name", "updated_at"])
        return user


class PublicProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    display_name = serializers.CharField(source="name", read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_own = serializers.SerializerMethodField()
    pix_enabled = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "username",
            "display_name",
            "bio",
            "avatar_url",
            "cover_url",
            "location",
            "website",
            "specialty",
            "pronouns",
            "is_available_for_work",
            "followers_count",
            "following_count",
            "posts_count",
            "is_following",
            "is_own",
            "pix_enabled",
        )

    def get_followers_count(self, obj):
        return obj.user.follower_links.count()

    def get_following_count(self, obj):
        return obj.user.following_links.count()

    def get_posts_count(self, obj):
        return obj.user.posts.filter(is_published=True).count()

    def get_is_following(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and Follow.objects.filter(follower=request.user, following=obj.user).exists()
        )

    def get_is_own(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.pk == obj.user_id)

    def get_pix_enabled(self, obj):
        return bool(obj.pix_key_ciphertext and obj.pix_receiver_name and obj.pix_city)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", required=False)
    email = serializers.EmailField(source="user.email", required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, trim_whitespace=False)
    pix_key = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=180)

    class Meta:
        model = Profile
        fields = (
            "username",
            "email",
            "display_name",
            "bio",
            "avatar_url",
            "cover_url",
            "location",
            "website",
            "specialty",
            "pronouns",
            "is_available_for_work",
            "pix_key_type",
            "pix_key",
            "pix_receiver_name",
            "pix_city",
            "password",
        )
        extra_kwargs = {field: {"required": False} for field in fields}

    def validate_username(self, value):
        normalized = value.lower().strip()
        if User.objects.exclude(pk=self.instance.user_id).filter(username__iexact=normalized).exists():
            raise serializers.ValidationError("Este nome de usuário já está em uso.")
        return normalized

    def validate_email(self, value):
        if User.objects.exclude(pk=self.instance.user_id).filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este e-mail já está em uso.")
        return value.lower()

    def validate_password(self, value):
        password_validation.validate_password(value, self.instance.user)
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        password = validated_data.pop("password", None)
        pix_key = validated_data.pop("pix_key", None)
        user = instance.user
        for field, value in user_data.items():
            setattr(user, field, value)
        if password:
            user.set_password(password)
            update_last_login(None, user)
        if user_data or password:
            user.save()
        if pix_key is not None:
            instance.set_pix_key(pix_key)
        return super().update(instance, validated_data)


class UserSummarySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source="profile.name", read_only=True)
    avatar_url = serializers.URLField(source="profile.avatar_url", read_only=True)
    specialty = serializers.CharField(source="profile.get_specialty_display", read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "display_name", "avatar_url", "specialty", "is_following")

    def get_is_following(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and Follow.objects.filter(follower=request.user, following=obj).exists())
