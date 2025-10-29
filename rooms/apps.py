# rooms/apps.py

# Import AppConfig from django.apps because it's the base class for a Django app configuration.
from django.apps import AppConfig

"""
Author: Angie
This class tells Django that an app named "rooms" exists.
This app handles the course rooms, discussion threads/posts,
and live study sessions features.
"""
# tells Django about this app: its name and default ID field type
class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rooms'
