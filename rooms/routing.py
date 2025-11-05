# rooms/routing.py

# Import path from django.urls because it's used to define WebSocket URL patterns.
from django.urls import path
# Import consumers from . because 'websocket_urlpatterns' needs the NotificationConsumer and RoomConsumer.
from . import consumers

"""
Author: Oju
This list defines the specific WebSocket addresses (URLs) that
the rooms app will listen to. It connects URLs for general
notifications and specific course rooms to the corresponding
consumer code that handles the real-time communication.
RT: This entire list configures the routing for real-time features
like presence, notifications, and live course room updates.
"""
websocket_urlpatterns = [
    # WebSocket path for personal notifications (like matches) and global presence (online status).
    path("ws/notifications/", consumers.NotificationConsumer.as_asgi()),
    # WebSocket path for a specific course room, identified by its 'slug'. Handles live thread/post broadcasts.
    path("ws/course_room/<slug:room_slug>/", consumers.RoomConsumer.as_asgi()),
]
