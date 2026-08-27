from django.db.models import Count, Exists, F, OuterRef, Prefetch, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Block, Follow
from apps.accounts.serializers import UserSummarySerializer
from apps.webapp.pagination import PulsoPagination
from apps.webapp.throttles import PostRateThrottle

from .models import Bookmark, Comment, Like, Notification, Post, Repost
from .serializers import CommentSerializer, NotificationSerializer, PostSerializer


def hidden_user_ids(user):
    blocked = Block.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    blocked_by = Block.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    return blocked, blocked_by


def visible_posts_for(user):
    blocked, blocked_by = hidden_user_ids(user)
    visible_comments = (
        Comment.objects.filter(parent__isnull=True, author__profile__is_hidden=False)
        .exclude(author_id__in=blocked)
        .exclude(author_id__in=blocked_by)
        .annotate(pulso_replies_count=Count("replies", distinct=True))
        .select_related("author", "author__profile")
        .order_by("-created_at")
    )
    return (
        Post.objects.filter(is_published=True)
        .filter(Q(author__profile__is_hidden=False) | Q(author=user))
        .exclude(author_id__in=blocked)
        .exclude(author_id__in=blocked_by)
        .annotate(
            pulso_is_liked=Exists(Like.objects.filter(post_id=OuterRef("pk"), user=user)),
            pulso_is_bookmarked=Exists(Bookmark.objects.filter(post_id=OuterRef("pk"), user=user)),
            pulso_is_reposted=Exists(Repost.objects.filter(post_id=OuterRef("pk"), user=user)),
            pulso_likes_count=Count("likes", distinct=True),
            pulso_comments_count=Count("comments", distinct=True),
            pulso_reposts_count=Count("reposts", distinct=True),
        )
        .select_related("author", "author__profile")
        .prefetch_related(
            Prefetch("comments", queryset=visible_comments, to_attr="pulso_visible_comments"),
        )
    )


def visible_people_relation(queryset, request, user_field):
    blocked, blocked_by = hidden_user_ids(request.user)
    filters = {f"{user_field}__profile__is_hidden": False}
    return queryset.filter(**filters).exclude(**{f"{user_field}_id__in": blocked}).exclude(**{f"{user_field}_id__in": blocked_by})


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    search_fields = ["body", "tags", "author__username", "author__profile__display_name"]
    ordering_fields = ["created_at"]
    filterset_fields = ["category", "author__username"]

    def get_queryset(self):
        return visible_posts_for(self.request.user)

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            return [permissions.IsAuthenticated(), IsPostAuthor()]
        return [permissions.IsAuthenticated()]

    def get_throttles(self):
        return [PostRateThrottle()] if self.action == "create" else super().get_throttles()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _toggle(self, model, request, post, notification_kind=None):
        relation, created = model.objects.get_or_create(post=post, user=request.user)
        if created and notification_kind and post.author != request.user:
            Notification.objects.create(recipient=post.author, actor=request.user, kind=notification_kind, post=post)
        if not created:
            relation.delete()
        return created

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        post = self.get_object()
        active = self._toggle(Like, request, post, Notification.Kind.LIKE)
        return Response({"liked": active, "count": Like.objects.filter(post=post).count()})

    @action(detail=True, methods=["get"])
    def likes(self, request, pk=None):
        post = self.get_object()
        likes = visible_people_relation(
            post.likes.select_related("user", "user__profile"),
            request,
            "user",
        ).order_by("-created_at")
        paginator = PulsoPagination()
        items = paginator.paginate_queryset(likes, request)
        users = [item.user for item in items]
        serializer = UserSummarySerializer(users, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"])
    def bookmark(self, request, pk=None):
        post = self.get_object()
        active = self._toggle(Bookmark, request, post)
        return Response({"bookmarked": active})

    @action(detail=True, methods=["post"])
    def repost(self, request, pk=None):
        post = self.get_object()
        active = self._toggle(Repost, request, post, Notification.Kind.REPOST)
        return Response({"reposted": active, "count": Repost.objects.filter(post=post).count()})

    @action(detail=True, methods=["get"], url_path="comment-preview")
    def comment_preview(self, request, pk=None):
        post = self.get_object()
        comments = visible_people_relation(
            post.comments.select_related("author", "author__profile").filter(parent__isnull=True),
            request,
            "author",
        ).order_by("-created_at")[:2]
        return Response(CommentSerializer(comments, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        post = self.get_object()
        if request.method == "GET":
            comments = visible_people_relation(
                post.comments.select_related("author", "author__profile"),
                request,
                "author",
            )
            return Response(CommentSerializer(comments, many=True, context={"request": request}).data)
        serializer = CommentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        parent = serializer.validated_data.get("parent")
        if parent and parent.post_id != post.pk:
            return Response({"detail": "Resposta inválida."}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(post=post, author=request.user)
        if post.author != request.user:
            Notification.objects.create(recipient=post.author, actor=request.user, kind=Notification.Kind.COMMENT, post=post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class IsPostAuthor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id


class FeedView(APIView):
    def get(self, request):
        following_ids = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
        followed_reposts = Repost.objects.filter(post_id=OuterRef("pk"), user_id__in=following_ids)
        posts = (
            visible_posts_for(request.user)
            .annotate(pulso_reposted_by_followed=Exists(followed_reposts))
            .filter(Q(author_id__in=following_ids) | Q(pulso_reposted_by_followed=True))
        )
        page = self.pagination_class()
        items = page.paginate_queryset(posts, request)
        serializer = PostSerializer(items, many=True, context={"request": request})
        return page.get_paginated_response(serializer.data)

    @staticmethod
    def pagination_class():
        return PulsoPagination()


class ExploreView(APIView):
    def get(self, request):
        posts = visible_posts_for(request.user).annotate(
            engagement=F("pulso_likes_count") + F("pulso_comments_count") * 2
        ).order_by("-engagement", "-created_at")
        category = request.query_params.get("category")
        if category:
            posts = posts.filter(category=category)
        paginator = PulsoPagination()
        items = paginator.paginate_queryset(posts, request)
        return paginator.get_paginated_response(PostSerializer(items, many=True, context={"request": request}).data)


class BookmarkListView(APIView):
    def get(self, request):
        posts = visible_posts_for(request.user).filter(bookmarks__user=request.user)
        return Response(PostSerializer(posts, many=True, context={"request": request}).data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related("actor", "actor__profile", "post")

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"updated": count})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"read": True})
