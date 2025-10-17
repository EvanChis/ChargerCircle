# accounts/admin.py

from django.contrib import admin
from .models import User, Profile, ProfileImage, BuddyRequest, SkippedMatch

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(ProfileImage)
admin.site.register(BuddyRequest)
admin.site.register(SkippedMatch)
