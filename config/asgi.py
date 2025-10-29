# config/asgi.py

# Import os because it's needed to set the 'DJANGO_SETTINGS_MODULE' environment variable.
import os
# Import get_asgi_application from django.core.asgi because 'django_asgi_app' needs it to handle standard HTTP requests.
from django.core.asgi import get_asgi_application
# Import ProtocolTypeRouter, URLRouter from channels.routing because 'application' needs them to split traffic.
from channels.routing import ProtocolTypeRouter, URLRouter
# Import AuthMiddlewareStack from channels.auth because 'application' needs it to give WebSockets access to the logged-in user.
from channels.auth import AuthMiddlewareStack
# Import routing from rooms because 'application' needs its list of WebSocket URLs.
from rooms import routing as rooms_routing
# Import routing from messaging because 'application' needs its list of WebSocket URLs.
from messaging import routing as messaging_routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

"""
Author:
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

