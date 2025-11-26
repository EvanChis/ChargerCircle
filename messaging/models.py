# messaging/models.py

# Import models from django.db because this file defines database models.
from django.db import models
# Import settings from django.conf because 'MessageThread' and 'Message' need to link to the User model.
from django.conf import settings

# Imports for image processing
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os

"""
Author: Cole
This class represents a single conversation thread between two
or more users. It primarily keeps track of who is involved
in the conversation ('participants') and when the last message
was sent ('updated_at'), which helps sort threads in the inbox.
RT: This model is used by the real-time chat system to identify
which users belong to a specific chat WebSocket group.
"""
class MessageThread(models.Model):
    # Optional name for the thread (e.g., "Session: Physics 101")
    name = models.CharField(max_length=255, blank=True, null=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='message_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.name:
            return self.name
        return f"Thread between {self.participants.count()} users"

"""
Author: Cole
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
    # MODIFICATION: Allow content to be blank (for image-only messages)
    content = models.TextField(blank=True)
    # Angie: Added an image field
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} in thread {self.thread.id}"

    # Optimization: Auto-resize image before saving
    def save(self, *args, **kwargs):
        if self.image:
            # We need to ensure the file pointer is at the start before we do anything
            if hasattr(self.image, 'seek'):
                self.image.seek(0)

            # Open the image using Pillow
            try:
                img = Image.open(self.image)
                
                # Convert to RGB if it's not (e.g. PNG with alpha) to save as JPEG
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Define max size (e.g., 1024x1024 for chat images)
                max_size = (1024, 1024)
                
                # Resize only if larger than max_size
                if img.height > max_size[1] or img.width > max_size[0]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Save the resized image to a BytesIO object
                    output = BytesIO()
                    img.save(output, format='JPEG', quality=75)
                    output.seek(0)
                    
                    # Replace the image field with the processed content
                    # We ensure the extension is .jpg since we converted to JPEG
                    new_name = os.path.splitext(self.image.name)[0] + '.jpg'
                    self.image = ContentFile(output.read(), name=new_name)
                else:
                    # CRITICAL FIX: If we didn't resize, we must reset the pointer 
                    # because Image.open() might have read from the file.
                    if hasattr(self.image, 'seek'):
                        self.image.seek(0)

            except Exception as e:
                print(f"Error optimizing image: {e}")
                # If optimization fails, we MUST reset the pointer to save the original
                if hasattr(self.image, 'seek'):
                    self.image.seek(0)

        super().save(*args, **kwargs)

