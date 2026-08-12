from rest_framework import serializers

from apps.accounts.serializers import UserSummarySerializer
from apps.common.media import MediaUploadError, store_image

from .models import Bookmark, Comment, Like, Notification, Post, Repost


class CommentSerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)
    replies_count = serializers.IntegerField(source="replies.count", read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "post", "author", "parent", "body", "replies_count", "created_at")
        read_only_fields = ("post", "author", "created_at")


class PostSerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    comments_count = serializers.IntegerField(source="comments.count", read_only=True)
    reposts_count = serializers.IntegerField(source="reposts.count", read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    is_reposted = serializers.SerializerMethodField()
    latest_comments = serializers.SerializerMethodField()
    tag_list = serializers.SerializerMethodField()
    image_upload = serializers.ImageField(write_only=True, required=False)
    pix_enabled = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "body",
            "category",
            "image_upload",
            "image_url",
            "video_url",
            "portfolio_url",
            "tags",
            "tag_list",
            "accepts_support",
            "pix_enabled",
            "likes_count",
            "comments_count",
            "reposts_count",
            "is_liked",
            "is_bookmarked",
            "is_reposted",
            "latest_comments",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("author", "image_url", "created_at", "updated_at")

    def validate(self, attrs):
        body = attrs.get("body", getattr(self.instance, "body", ""))
        has_existing_media = bool(
            self.instance
            and any(getattr(self.instance, field, "") for field in ("image_url", "video_url", "portfolio_url"))
        )
        has_new_media = bool(attrs.get("image_upload") or any(attrs.get(field) for field in ("video_url", "portfolio_url")))
        if not body.strip() and not has_existing_media and not has_new_media:
            raise serializers.ValidationError("Conte uma história ou adicione uma imagem ou portfólio.")
        return attrs

    def _store_upload(self, validated_data):
        upload = validated_data.pop("image_upload", None)
        if not upload:
            return validated_data
        try:
            validated_data["image_url"] = store_image(upload, "posts", self.context.get("request"))
        except MediaUploadError as exc:
            raise serializers.ValidationError({"image_upload": str(exc)}) from exc
        return validated_data

    def create(self, validated_data):
        return super().create(self._store_upload(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._store_upload(validated_data))

    def validate_tags(self, value):
        tags = [tag.strip().lstrip("#").lower() for tag in value.split(",") if tag.strip()]
        if len(tags) > 8:
            raise serializers.ValidationError("Use no máximo 8 tags.")
        return ",".join(dict.fromkeys(tags))

    def _has(self, model, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and model.objects.filter(post=obj, user=request.user).exists())

    def get_is_liked(self, obj):
        return self._has(Like, obj)

    def get_is_bookmarked(self, obj):
        return self._has(Bookmark, obj)

    def get_is_reposted(self, obj):
        return self._has(Repost, obj)

    def get_latest_comments(self, obj):
        comments = obj.comments.select_related("author", "author__profile").filter(parent__isnull=True)[:2]
        return CommentSerializer(comments, many=True, context=self.context).data

    def get_tag_list(self, obj):
        return [tag for tag in obj.tags.split(",") if tag]

    def get_pix_enabled(self, obj):
        profile = obj.author.profile
        return bool(obj.accepts_support and profile.pix_key_ciphertext and profile.pix_receiver_name and profile.pix_city)


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)
    post_excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ("id", "actor", "kind", "post", "post_excerpt", "is_read", "created_at")

    def get_post_excerpt(self, obj):
        return obj.post.body[:80] if obj.post else ""
