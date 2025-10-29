# messaging/admin.py

# Import admin from django.contrib because this file configures the admin site.
from django.contrib import admin
# Import models from .models because 'MessageThread' and 'Message' need to be registered.
from .models import MessageThread, Message

"""
Author:
This block of code makes the messaging database tables
('MessageThread' and 'Message') visible in the Django
admin control panel. This allows an administrator to
manually view or edit chat threads and individual messages.
"""
admin.site.register(MessageThread)
admin.site.register(Message)
