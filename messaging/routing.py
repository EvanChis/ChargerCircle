# messaging/routing.py

# Import re_path from django.urls because it's used to define URL patterns with regular expressions for WebSockets.
from django.urls import re_path
# Import consumers from . because 'websocket_urlpatterns' needs the ChatConsumer.
from . import consumers

"""
Author:
This list defines the specific WebSocket addresses (URLs) that
the messaging app will listen to. It connects the URL for a
chat thread (like '/ws/chat/123/') to the 'ChatConsumer' code
that handles the real-time communication for that chat.
RT: This is the routing configuration for the real-time private chat feature.
"""
websocket_urlpatterns = [
    # This pattern matches WebSocket connections for a specific chat thread ID.
    re_path(r'ws/chat/(?P<thread_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
