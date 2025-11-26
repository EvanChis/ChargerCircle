# config/asgi.py

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from rooms import routing as rooms_routing
from messaging import routing as messaging_routing

"""
Author: Evan
This file is the main entry-point for the server. It acts as
a traffic controller that splits incoming connections.
It sends all normal web page (HTTP) requests to Django, and
sends all real-time (WebSocket) requests to the 'channels'
routing system.
RT: This is the core file that "turns on" all real-time features
by directing WebSocket traffic to the 'rooms' and 'messaging' apps.
"""
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            rooms_routing.websocket_urlpatterns + 
            messaging_routing.websocket_urlpatterns
        )
    ),
})
