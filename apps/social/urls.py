from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookmarkListView, ExploreView, FeedView, NotificationViewSet, PostViewSet

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("feed/", FeedView.as_view(), name="feed"),
    path("explore/", ExploreView.as_view(), name="explore"),
    path("bookmarks/", BookmarkListView.as_view(), name="bookmarks"),
    path("", include(router.urls)),
]
