# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from .views import home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz/', lambda r: HttpResponse("ok", content_type="text/plain")),
    
    # App URLs
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('rooms/', include('rooms.urls')),
    path('messages/', include('messaging.urls')),
]

# This is only for serving user-uploaded media files during local development.
# In production, a web server like Nginx would handle this.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
