import re

from django.contrib.auth import password_validation
from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework import serializers

from apps.common.media import MediaUploadError, store_image

from .models import Block, Follow, Profile, User


RANDOM_PIX_KEY_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


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
    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    display_name = serializers.CharField(source="name", read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_own = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    pix_enabled = serializers.SerializerMethodField()
    specialty_label = serializers.CharField(source="get_specialty_display", read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id",
            "username",
            "display_name",
            "bio",
            "avatar_url",
            "cover_url",
            "cover_position_y",
            "location",
            "website",
            "instagram_url",
            "github_url",
            "linkedin_url",
            "behance_url",
            "specialty",
            "specialty_label",
            "pronouns",
            "is_available_for_work",
            "pix_key_type",
            "pix_receiver_name",
            "pix_city",
            "followers_count",
            "following_count",
            "posts_count",
            "is_following",
            "is_own",
            "is_blocked",
            "pix_enabled",
        )

    def _hidden_connection_ids(self):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return (), ()
        blocked = Block.objects.filter(blocker=request.user).values_list("blocked_id", flat=True)
        blocked_by = Block.objects.filter(blocked=request.user).values_list("blocker_id", flat=True)
        return blocked, blocked_by

    def get_followers_count(self, obj):
        blocked, blocked_by = self._hidden_connection_ids()
        return (
            obj.user.follower_links.filter(
                follower__profile__is_hidden=False,
                follower__is_staff=False,
                follower__is_superuser=False,
            )
            .exclude(follower_id__in=blocked)
            .exclude(follower_id__in=blocked_by)
            .count()
        )

    def get_following_count(self, obj):
        blocked, blocked_by = self._hidden_connection_ids()
        return (
            obj.user.following_links.filter(
                following__profile__is_hidden=False,
                following__is_staff=False,
                following__is_superuser=False,
            )
            .exclude(following_id__in=blocked)
            .exclude(following_id__in=blocked_by)
            .count()
        )

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

    def get_is_blocked(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and request.user.pk != obj.user_id
            and Block.objects.filter(blocker=request.user, blocked=obj.user).exists()
        )

    def get_pix_enabled(self, obj):
        return bool(
            obj.pix_key_type == "random"
            and obj.pix_key_ciphertext
            and obj.pix_receiver_name
            and obj.pix_city
        )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", required=False)
    email = serializers.EmailField(source="user.email", required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, trim_whitespace=False)
    pix_key = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=180)
    avatar_upload = serializers.ImageField(write_only=True, required=False)
    cover_upload = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = Profile
        fields = (
            "username",
            "email",
            "display_name",
            "bio",
            "avatar_upload",
            "cover_upload",
            "cover_position_y",
            "location",
            "website",
            "instagram_url",
            "github_url",
            "linkedin_url",
            "behance_url",
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

    def validate_pix_key_type(self, value):
        normalized = value.strip().lower()
        if normalized not in {"", "random"}:
            raise serializers.ValidationError("A PULSO aceita apenas chave Pix aleatória.")
        return normalized

    def validate_pix_key(self, value):
        normalized = value.strip().lower()
        if normalized and not RANDOM_PIX_KEY_RE.fullmatch(normalized):
            raise serializers.ValidationError(
                "Use uma chave Pix aleatória válida, no formato gerado pelo seu banco."
            )
        return normalized

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "pix_key" in attrs:
            attrs["pix_key_type"] = "random" if attrs["pix_key"] else ""
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        password = validated_data.pop("password", None)
        pix_key = validated_data.pop("pix_key", None)
        avatar_upload = validated_data.pop("avatar_upload", None)
        cover_upload = validated_data.pop("cover_upload", None)
        request = self.context.get("request")
        try:
            if avatar_upload:
                validated_data["avatar_url"] = store_image(avatar_upload, "profiles/avatars", request)
            if cover_upload:
                validated_data["cover_url"] = store_image(cover_upload, "profiles/covers", request)
        except MediaUploadError as exc:
            raise serializers.ValidationError({"image": str(exc)}) from exc
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
        if not request or not request.user.is_authenticated:
            return False

        cache_name = "_pulso_following_ids"
        following_ids = getattr(request, cache_name, None)
        if following_ids is None:
            following_ids = set(
                Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
            )
            setattr(request, cache_name, following_ids)
        return obj.pk in following_ids
