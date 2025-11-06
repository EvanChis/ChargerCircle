# messaging/urls.py

# Import path from django.urls because it's needed to define URL routes.
from django.urls import path
# MODIFICATION: Import view for images
from .views import inbox_view, upload_chat_image_view

"""
Author: Cole
This file defines the web addresses (URLs) for the 'messaging'
app. It maps the URL for the main inbox page and the URL for a
specific conversation to the 'inbox_view' function, which handles
displaying the correct chat interface.
"""
urlpatterns = [
    # Route for the main inbox page (no specific thread selected)
    path('', inbox_view, name='inbox'),
    
    # Route for handling image uploads
    path('upload-image/<int:thread_id>/', upload_chat_image_view, name='upload_chat_image'),
    
    # Route for viewing a specific conversation thread
    path('<int:thread_id>/', inbox_view, name='conversation'),
]
