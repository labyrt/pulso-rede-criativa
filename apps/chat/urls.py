from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CallViewSet, ConversationViewSet, IceServerView

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("calls", CallViewSet, basename="call")
router.register("ice-servers", IceServerView, basename="ice-servers")

urlpatterns = [path("", include(router.urls))]
