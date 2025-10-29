# rooms/urls.py

# Import path from django.urls because it's needed to define each URL route.
from django.urls import path
# Import views from .views because all the functions that handle page loads and HTMX requests are here.
from .views import (
    course_list_view, course_detail_view, thread_detail_view,
    create_session_view, accept_session_invite, decline_session_invite,
    session_detail_view, delete_session_view, leave_session_view,
    session_participants_view,
    edit_post_view, delete_post_view,
)

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This file is the "address book" for the 'rooms' application.
It maps specific web addresses (URLs) related to courses,
threads, posts, and sessions to the correct Python function
(a "view") that handles the request.
RT: This file defines several URLs used for HTMX requests, such
as editing/deleting posts, accepting/declining session invites,
and getting the updated participant list for a session.
"""
urlpatterns = [
    # Main page showing the list of all course rooms
    path('', course_list_view, name='course_list'),
    
    # Post URLs
    path('post/edit/<int:pk>/', edit_post_view, name='edit_post'), # RT: HTMX URL for getting the post edit form
    path('post/delete/<int:pk>/', delete_post_view, name='delete_post'), # RT: HTMX URL for deleting a post

    # Session URLs
    path('sessions/create/', create_session_view, name='create_session'), # Page to create a new session
    path('sessions/<int:pk>/', session_detail_view, name='session_detail'), # Page showing details of one session
    path('sessions/<int:pk>/delete/', delete_session_view, name='delete_session'), # Action to delete a session
    path('sessions/<int:pk>/leave/', leave_session_view, name='leave_session'), # Action to leave a session
    # RT: HTMX URL to periodically fetch the updated participant list for a session
    path('sessions/<int:pk>/participants/', session_participants_view, name='session_participants'),
    # RT: HTMX URL for accepting a session invite (updates the message in chat)
    path('sessions/invites/accept/<int:session_id>/<int:message_id>/', accept_session_invite, name='accept_session_invite'),
    # RT: HTMX URL for declining a session invite (updates the message in chat)
    path('sessions/invites/decline/<int:session_id>/<int:message_id>/', decline_session_invite, name='decline_session_invite'),
    
    # Generic slug-based paths for course rooms and threads
    path('<slug:slug>/', course_detail_view, name='course_detail'), # Page for a specific course room (shows threads)
    path('<slug:slug>/<int:pk>/', thread_detail_view, name='thread_detail'), # Page for a specific discussion thread (shows posts)
]
