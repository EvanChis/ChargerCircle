# accounts/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    signup_view, logout_view, dashboard_view, discover_view, skip_match_view,
    buddies_view, sessions_view, remove_buddy, profile_view, edit_profile_view,
    set_main_profile_image, delete_profile_image, like_user_view, undo_action_view,
    delete_account_view, verify_email,
    PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView,
)

urlpatterns = [
    # Auth
    path('signup/', signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Verification
    path('verify/<uidb64>/<token>/', verify_email, name='verify_email'),

    # Password Reset
    path('password_reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset/confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password_reset/complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Core Pages
    path('dashboard/', dashboard_view, name='dashboard'),
    path('discover/', discover_view, name='discover'),
    path('buddies/', buddies_view, name='buddies'),
    path('sessions/', sessions_view, name='sessions'),

    # Profile URLs
    path('profile/', profile_view, name='my_profile'),
    path('profile/edit/', edit_profile_view, name='edit_profile'),
    path('profile/<int:pk>/', profile_view, name='profile'),
    path('profile/delete/', delete_account_view, name='delete_account'),
    path('profile/image/set-main/<int:pk>/', set_main_profile_image, name='set_main_profile_image'),
    path('profile/image/delete/<int:pk>/', delete_profile_image, name='delete_profile_image'),
    
    # Matching URLs
    path('discover/like/<int:pk>/', like_user_view, name='like_user'),
    path('discover/skip/<int:pk>/', skip_match_view, name='skip_match'),
    path('buddy/remove/<int:pk>/', remove_buddy, name='remove_buddy'),
    path('buddy/undo/<int:pk>/', undo_action_view, name='undo_action'),
]
