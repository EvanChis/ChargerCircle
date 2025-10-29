# config/urls.py

# Import admin from django.contrib because 'urlpatterns' needs it for the admin site route.
from django.contrib import admin
# Import path, include from django.urls because 'urlpatterns' needs them to define routes.
from django.urls import path, include
# Import settings from django.conf because the 'if settings.DEBUG' block needs it.
from django.conf import settings
# Import static from django.conf.urls.static because the 'if settings.DEBUG' block needs it.
from django.conf.urls.static import static
# Import HttpResponse from django.http because the 'healthz' path needs it.
from django.http import HttpResponse
# Import home_view from .views because 'urlpatterns' needs it for the home page route.
from .views import home_view

"""
Author:
This is the master "address book" for the entire project.
It defines the main URL patterns for the whole site. It mostly
just directs traffic to the more specific 'urls.py' files
inside each app (like 'accounts.urls', 'rooms.urls', etc.).
RT: This file is responsible for including the URL files from
other apps, which in turn contain all the real-time HTMX routes.
"""
urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz/', lambda r: HttpResponse("ok", content_type="text/plain")),
    
    # App URLs
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')), # RT: Includes all HTMX routes from the 'accounts' app
    path('rooms/', include('rooms.urls')), # RT: Includes all HTMX routes from the 'rooms' app
    path('messages/', include('messaging.urls')),
]

"""
Author:
This block of code is a helper just for local development.
It tells Django how to serve user-uploaded files (like
profile pictures) so we can see them on the local test
server. This code does *not* run in production.
"""
# This is only for serving user-uploaded media files during local development.
# In production, a web server like Nginx will handle this.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

