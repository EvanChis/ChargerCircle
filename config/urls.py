# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import HttpResponse
from .views import home_view
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz/', lambda r: HttpResponse("ok", content_type="text/plain")),
    
    # App URLs
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('rooms/', include('rooms.urls')),
    path('messages/', include('messaging.urls')),
]

# Local media serving
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
