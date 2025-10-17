# messaging/urls.py

from django.urls import path
from .views import inbox_view

urlpatterns = [
    path('', inbox_view, name='inbox'),
    path('<int:thread_id>/', inbox_view, name='conversation'),
]
