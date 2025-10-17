# rooms/urls.py

from django.urls import path
from .views import (
    course_list_view, course_detail_view, thread_detail_view,
    create_session_view, accept_session_invite, decline_session_invite,
    session_detail_view, delete_session_view, leave_session_view,
    session_participants_view, # <-- New
    edit_post_view, delete_post_view,
)

urlpatterns = [
    path('', course_list_view, name='course_list'),
    
    # Post URLs
    path('post/edit/<int:pk>/', edit_post_view, name='edit_post'),
    path('post/delete/<int:pk>/', delete_post_view, name='delete_post'),

    # Session URLs
    path('sessions/create/', create_session_view, name='create_session'),
    path('sessions/<int:pk>/', session_detail_view, name='session_detail'),
    path('sessions/<int:pk>/delete/', delete_session_view, name='delete_session'),
    path('sessions/<int:pk>/leave/', leave_session_view, name='leave_session'),
    path('sessions/<int:pk>/participants/', session_participants_view, name='session_participants'), # <-- New
    path('sessions/invites/accept/<int:session_id>/<int:message_id>/', accept_session_invite, name='accept_session_invite'),
    path('sessions/invites/decline/<int:session_id>/<int:message_id>/', decline_session_invite, name='decline_session_invite'),
    
    # Generic slug-based paths
    path('<slug:slug>/', course_detail_view, name='course_detail'),
    path('<slug:slug>/<int:pk>/', thread_detail_view, name='thread_detail'),
]
