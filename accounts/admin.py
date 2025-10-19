# accounts/admin.py

from django.contrib import admin
from .models import User, Profile, ProfileImage, Like, SkippedMatch

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(ProfileImage)
admin.site.register(Like)
admin.site.register(SkippedMatch)
