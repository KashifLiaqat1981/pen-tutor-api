# routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # Accept both UUID format and integer format
    re_path(r'ws/chat/(?P<room_id>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
]
