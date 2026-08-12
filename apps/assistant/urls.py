from django.urls import path

from .views import CaptionAssistantView

urlpatterns = [path("caption/", CaptionAssistantView.as_view(), name="caption-assistant")]
