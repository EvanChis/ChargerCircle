# accounts/urls.py

# Import path from django.urls because it's needed to define each URL route.
from django.urls import path
# Import auth_views from django.contrib.auth because the built-in 'login' view is used.
from django.contrib.auth import views as auth_views
# Import views from .views because all the custom functions that handle page loads are here.
from .views import (
    signup_view, logout_view, dashboard_view, discover_view, skip_match_view,
    buddies_view, sessions_view, remove_buddy, profile_view, edit_profile_view,
    set_main_profile_image, delete_profile_image, like_user_view, undo_action_view,
)

"""
Author:
This file is the main "address book" or "table of contents"
for the 'accounts' application. It maps a specific web
address (URL) to the correct Python function (a "view")
that knows how to handle it. For example, it says that
when a user visits "/signup/", it should run the 'signup_view'
function.
RT: This file defines several URLs (like 'like_user' and
'skip_match') that are specifically for handling real-time
HTMX requests from the Discover and Profile pages.
"""
urlpatterns = [
    # Auth
    path('signup/', signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),

    # Core Pages
    path('dashboard/', dashboard_view, name='dashboard'),
    path('discover/', discover_view, name='discover'),
    path('buddies/', buddies_view, name='buddies'),
    path('sessions/', sessions_view, name='sessions'),

    # Profile URLs
    path('profile/', profile_view, name='my_profile'),
    path('profile/edit/', edit_profile_view, name='edit_profile'),
    path('profile/<int:pk>/', profile_view, name='profile'),
    # RT: HTMX URL for setting the main profile picture
    path('profile/image/set-main/<int:pk>/', set_main_profile_image, name='set_main_profile_image'),
    # RT: HTMX URL for deleting a profile picture
    path('profile/image/delete/<int:pk>/', delete_profile_image, name='delete_profile_image'),
    
    # Matching URLs
    # RT: HTMX URL for liking a user
    path('discover/like/<int:pk>/', like_user_view, name='like_user'),
    # RT: HTMX URL for skipping a user
    path('discover/skip/<int:pk>/', skip_match_view, name='skip_match'),
    # RT: HTMX URL for removing a buddy
    path('buddy/remove/<int:pk>/', remove_buddy, name='remove_buddy'),
    # RT: HTMX URL for undoing a skip or like
    path('buddy/undo/<int:pk>/', undo_action_view, name='undo_action'),
]
