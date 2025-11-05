# accounts/admin.py

# Import admin from django.contrib because this file configures the admin site.
from django.contrib import admin
# Import models from .models because User, Profile, ProfileImage, Like, SkippedMatch need to be registered.
from .models import User, Profile, ProfileImage, Like, SkippedMatch

"""
Author: Evan
This block of code makes the user database tables visible
in the Django admin control panel. This allows an
administrator to manually view or edit user data, profiles,
images, likes, and skips.
"""
admin.site.register(User)
admin.site.register(Profile)
admin.site.register(ProfileImage)
admin.site.register(Like)
admin.site.register(SkippedMatch)
