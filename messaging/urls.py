# messaging/urls.py

# Import path from django.urls because it's needed to define URL routes.
from django.urls import path
# Import views from .views because we need to map URLs to these functions.
from .views import inbox_view, upload_chat_image_view, leave_thread_view

"""
Author: Cole
This file defines the web addresses (URLs) for the 'messaging'
app. It maps the URL for the main inbox page, image uploads,
leaving threads, and specific conversations to their respective views.
"""
urlpatterns = [
    # Route for the main inbox page (no specific thread selected)
    path('', inbox_view, name='inbox'),
    
    # Route for handling image uploads
    path('upload-image/<int:thread_id>/', upload_chat_image_view, name='upload_chat_image'),
    
    # Route for leaving a group chat
    path('leave/<int:thread_id>/', leave_thread_view, name='leave_thread'),

    # Route for viewing a specific conversation thread
    path('<int:thread_id>/', inbox_view, name='conversation'),
]
