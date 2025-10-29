# core/apps.py

# Import AppConfig from django.apps because it's the base class for a Django app configuration.
from django.apps import AppConfig

"""
Author:
This class tells Django that an app named "core" exists.
This app is often used for essential, project-wide code
(like the 'utils.py' file) that doesn't belong to just one
feature like 'accounts' or 'rooms'.
"""
class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

