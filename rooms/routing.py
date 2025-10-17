# rooms/routing.py

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/notifications/", consumers.NotificationConsumer.as_asgi()),
    path("ws/course_room/<slug:room_slug>/", consumers.RoomConsumer.as_asgi()),
]
