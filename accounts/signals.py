# accounts/signals.py

# Import post_save from django.db.models.signals because we need to listen for when a model is saved.
from django.db.models.signals import post_save
# Import receiver from django.dispatch because it's the decorator used to connect a function to a signal.
from django.dispatch import receiver
# Import models from .models because 'User' is the sender of the signal and 'Profile' is what we create.
from .models import User, Profile

"""
Author: Evan
This function is a "signal receiver." It automatically runs
every time a new 'User' account is created (saved for the
first time). Its job is to instantly create a matching,
empty 'Profile' for that new user. This ensures that every
user always has a profile associated with their account.
"""
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

