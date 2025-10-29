# accounts/apps.py

# Import AppConfig from django.apps because it's the base class for a Django app configuration.
from django.apps import AppConfig

"""
Author: Evan
This class tells Django how to treat the "accounts" app. It
sets the app's name and also runs a special "ready" function
when the app first loads. This "ready" function is used to
import the "signals.py" file, which makes sure that a new
Profile is automatically created every time a new User account
is made.
"""
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals

