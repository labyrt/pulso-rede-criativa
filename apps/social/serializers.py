from rest_framework import serializers

from apps.accounts.serializers import UserSummarySerializer

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

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "body",
            "category",
            "image_url",
            "video_url",
            "portfolio_url",
            "tags",
            "tag_list",
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
        read_only_fields = ("author", "created_at", "updated_at")

    def validate(self, attrs):
        if not attrs.get("body", "").strip() and not any(attrs.get(field) for field in ("image_url", "video_url", "portfolio_url")):
            raise serializers.ValidationError("Conte uma história ou adicione um link criativo.")
        return attrs

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


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)
    post_excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ("id", "actor", "kind", "post", "post_excerpt", "is_read", "created_at")

    def get_post_excerpt(self, obj):
        return obj.post.body[:80] if obj.post else ""
