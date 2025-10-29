# messaging/models.py

# Import models from django.db because this file defines database models.
from django.db import models
# Import settings from django.conf because 'MessageThread' and 'Message' need to link to the User model.
from django.conf import settings

"""
Author:
This class represents a single conversation thread between two
or more users. It primarily keeps track of who is involved
in the conversation ('participants') and when the last message
was sent ('updated_at'), which helps sort threads in the inbox.
RT: This model is used by the real-time chat system to identify
which users belong to a specific chat WebSocket group.
"""
class MessageThread(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='message_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Thread between {self.participants.count()} users"

"""
Author:
This class represents a single message within a MessageThread.
It stores the actual text content of the message, who sent it
('sender'), and exactly when it was sent ('timestamp'). It's
linked back to the specific 'thread' it belongs to.
RT: New 'Message' objects are created and saved in real-time
when users send messages via the WebSocket chat. Session invite
messages also use this model.
"""
class Message(models.Model):
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} in thread {self.thread.id}"
