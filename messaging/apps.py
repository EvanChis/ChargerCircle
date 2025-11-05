# messaging/apps.py

# Import AppConfig from django.apps because it's the base class for a Django app configuration.
from django.apps import AppConfig

"""
Author: Cole
This class tells Django that an app named "messaging" exists.
This app handles all the private chat features, including
storing messages and managing real-time chat connections.
RT: This app contains the WebSocket consumers for real-time chat.
"""
class MessagingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging'
