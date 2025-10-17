# accounts/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    signup_view, logout_view, dashboard_view, discover_view, skip_match_view,
    buddies_view, sessions_view, send_buddy_request, accept_buddy_request,
    decline_buddy_request, remove_buddy, profile_view, edit_profile_view,
    set_main_profile_image, delete_profile_image,
)

urlpatterns = [
    # Auth
    path('signup/', signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),

    # Core Pages
    path('dashboard/', dashboard_view, name='dashboard'),
    path('discover/', discover_view, name='discover'),
    path('discover/skip/<int:pk>/', skip_match_view, name='skip_match'),
    path('buddies/', buddies_view, name='buddies'),
    path('sessions/', sessions_view, name='sessions'),

    # Profile URLs
    path('profile/', profile_view, name='my_profile'),
    path('profile/edit/', edit_profile_view, name='edit_profile'),
    path('profile/<int:pk>/', profile_view, name='profile'), # UPDATED
    path('profile/image/set-main/<int:pk>/', set_main_profile_image, name='set_main_profile_image'),
    path('profile/image/delete/<int:pk>/', delete_profile_image, name='delete_profile_image'),
    
    # Buddy Request URLs
    path('buddy-request/send/<int:pk>/', send_buddy_request, name='send_buddy_request'),
    path('buddy-request/accept/<int:request_id>/', accept_buddy_request, name='accept_buddy_request'),
    path('buddy-request/decline/<int:request_id>/', decline_buddy_request, name='decline_buddy_request'),
    path('buddy/remove/<int:pk>/', remove_buddy, name='remove_buddy'),
]
