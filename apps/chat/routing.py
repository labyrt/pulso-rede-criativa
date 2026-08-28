from django.urls import re_path

from .consumers import ConversationConsumer
from .events import UserEventsConsumer

websocket_urlpatterns = [
    re_path(r"^ws/events/$", UserEventsConsumer.as_asgi()),
    re_path(r"^ws/chat/(?P<conversation_id>\d+)/$", ConversationConsumer.as_asgi()),
]
