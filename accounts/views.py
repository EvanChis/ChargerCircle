# accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.template.loader import render_to_string
from django.contrib import messages


from .forms import CustomUserCreationForm, ProfileImageForm, ProfileUpdateForm, CustomPasswordResetForm
from .services import find_matches
from .models import ProfileImage, SkippedMatch, Like
from rooms.models import Course, Session
from messaging.utils import get_or_create_message_thread
from core.utils import get_online_user_ids

User = get_user_model()

# Helper function to check for a match and create a friendship
def check_for_match(user1, user2):
    # Checks if user2 has also liked user1
    if Like.objects.filter(from_user=user2, to_user=user1).exists():
        # Is a match
        user1.buddies.add(user2)
        user2.buddies.add(user1)

        # Cleans up the Like objects
        Like.objects.filter(from_user=user1, to_user=user2).delete()
        Like.objects.filter(from_user=user2, to_user=user1).delete()
        
        # Creates a message thread for the matched users
        get_or_create_message_thread([user1, user2])

        # Sends notifications to both users
        channel_layer = get_channel_layer()
        
        group_name_1 = f'notifications_for_user_{user1.pk}'
        message_1 = { 'type': 'send_notification', 'message': { 'text': f'You matched with {user2.first_name}!' } }
        async_to_sync(channel_layer.group_send)(group_name_1, message_1)
        
        group_name_2 = f'notifications_for_user_{user2.pk}'
        message_2 = { 'type': 'send_notification', 'message': { 'text': f'You matched with {user1.first_name}!' } }
        async_to_sync(channel_layer.group_send)(group_name_2, message_2)

        return True
    return False


@login_required
@require_POST
def like_user_view(request, pk):
    liked_user = get_object_or_404(User, pk=pk)
    
    if liked_user != request.user:
        Like.objects.get_or_create(from_user=request.user, to_user=liked_user)
        check_for_match(request.user, liked_user)

    matches = find_matches(request.user)
    next_match = matches[0] if matches else None
    if next_match:
        return render(request, 'accounts/partials/match_card.html', {'match': next_match})
    else:
        return render(request, 'accounts/partials/no_more_matches.html')

@login_required
@require_POST
def remove_buddy(request, pk):
    buddy_to_remove = get_object_or_404(User, pk=pk)
    
    # Removes the match
    request.user.buddies.remove(buddy_to_remove)
    buddy_to_remove.buddies.remove(request.user)
    
    # Creates a SkippedMatch entry so they don't see each other in Discover
    # Creates one for the current user so they can undo it.
    skipped_entry = SkippedMatch.objects.create(from_user=request.user, skipped_user=buddy_to_remove)
    
    # Also creates a reverse entry so the other user doesn't see them either
    SkippedMatch.objects.get_or_create(from_user=buddy_to_remove, skipped_user=request.user)
    
    # Renders the "undo" item to be sent out-of-band
    undo_item_html = render_to_string(
        'accounts/partials/undo_item.html',
        {'skipped': skipped_entry},
        request=request
    )
    
    # Returns an empty response for the buddy list item, and the OOB item
    response = HttpResponse()
    response.write(f'<div hx-swap-oob="afterbegin:#undo-list">{undo_item_html}</div>')
    return response

@login_required
@require_POST
def undo_action_view(request, pk):
    skipped_entry = get_object_or_404(SkippedMatch, pk=pk, from_user=request.user)
    
    # Checks for buddy removal
    try:
        reverse_entry = SkippedMatch.objects.get(from_user=skipped_entry.skipped_user, skipped_user=request.user)
        # Restores a match
        request.user.buddies.add(skipped_entry.skipped_user)
        skipped_entry.skipped_user.buddies.add(request.user)
        reverse_entry.delete()
    except SkippedMatch.DoesNotExist:
        # Wasn't a previous match so no match to restore
        pass

    skipped_entry.delete()

    # Re-render buddy list and undo list
    buddy_list = request.user.buddies.all()
    online_user_ids = get_online_user_ids()
    buddy_list_html = render_to_string(
        'accounts/partials/buddy_list.html',
        {'buddy_list': buddy_list, 'online_user_ids': online_user_ids},
        request=request
    )
    
    last_skipped = SkippedMatch.objects.filter(from_user=request.user)[:10]
    undo_list_html = render_to_string(
        'accounts/partials/undo_list.html',
        {'last_skipped': last_skipped},
        request=request
    )
    
    # Return a response that updates both the buddy list and undo list
    response = HttpResponse()
    response.write(f'<div id="buddy-list-container" hx-swap-oob="outerHTML">{buddy_list_html}</div>')
    response.write(f'<div id="undo-list-container" hx-swap-oob="outerHTML">{undo_list_html}</div>')
    
    return response

@login_required
def buddies_view(request):
    buddy_list = request.user.buddies.all()
    online_user_ids = get_online_user_ids()
    last_skipped = SkippedMatch.objects.filter(from_user=request.user)[:10]

    context = {
        'buddy_list': buddy_list,
        'online_user_ids': online_user_ids,
        'last_skipped': last_skipped,
    }
    return render(request, 'accounts/buddies.html', context)


# More views
@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                hangout_course = Course.objects.get(slug='hang-out')
                user.courses.add(hangout_course)
            except Course.DoesNotExist:
                pass
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def discover_view(request):
    matches = find_matches(request.user)
    next_match = matches[0] if matches else None
    context = {'match': next_match}
    return render(request, 'accounts/discover.html', context)

@login_required
@require_POST
def skip_match_view(request, pk):
    skipped_user = get_object_or_404(User, pk=pk)
    SkippedMatch.objects.get_or_create(from_user=request.user, skipped_user=skipped_user)
    matches = find_matches(request.user)
    next_match = matches[0] if matches else None
    if next_match:
        return render(request, 'accounts/partials/match_card.html', {'match': next_match})
    else:
        return render(request, 'accounts/partials/no_more_matches.html')

@login_required
def sessions_view(request):
    my_sessions = Session.objects.filter(participants=request.user)
    context = {'my_sessions': my_sessions}
    return render(request, 'accounts/sessions.html', context)
@login_required
def profile_view(request, pk=None):
    if pk:
        profile_user = get_object_or_404(User, pk=pk)
    else:
        profile_user = request.user
    thread = None
    if profile_user != request.user:
        thread = get_or_create_message_thread([request.user, profile_user])
    
    profile_images = profile_user.profile.images.order_by('-is_main', '-uploaded_at')

    context = {
        'profile_user': profile_user,
        'thread': thread,
        'profile_images': profile_images,
    }
    return render(request, 'accounts/profile.html', context)

def get_profile_editor_context(request):
    profile = request.user.profile
    image_form = ProfileImageForm()
    profile_images = profile.images.order_by('-is_main', '-uploaded_at')
    update_form = ProfileUpdateForm(instance=request.user, initial={
        'bio': profile.bio,
        'courses': request.user.courses.all(),
    })
    return {'image_form': image_form, 'update_form': update_form, 'profile_images': profile_images}

@login_required
def edit_profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        if 'image' in request.FILES:
            image_form = ProfileImageForm(request.POST, request.FILES)
            if image_form.is_valid() and profile.images.count() < 5:
                profile_image = image_form.save(commit=False)
                profile_image.profile = profile
                if profile.images.count() == 0:
                    profile_image.is_main = True
                profile_image.save()
            context = get_profile_editor_context(request)
            return render(request, 'accounts/partials/profile_editor.html', context)
        else:
            update_form = ProfileUpdateForm(request.POST, instance=request.user)
            if update_form.is_valid():
                user = update_form.save(commit=False)
                user.save()
                
                profile.bio = update_form.cleaned_data['bio']
                profile.save()
                
                user.courses.set(update_form.cleaned_data['courses'])
            return redirect('edit_profile')
    
    context = get_profile_editor_context(request)
    return render(request, 'accounts/edit_profile.html', context)

@login_required
@require_POST
def set_main_profile_image(request, pk):
    profile = request.user.profile
    image = get_object_or_404(ProfileImage, pk=pk, profile=profile)
    profile.images.update(is_main=False)
    image.is_main = True
    image.save()
    context = get_profile_editor_context(request)
    return render(request, 'accounts/partials/profile_editor.html', context)

@login_required
@require_POST
def delete_profile_image(request, pk):
    profile = request.user.profile
    image = get_object_or_404(ProfileImage, pk=pk, profile=profile)
    was_main = image.is_main
    image.delete()
    if was_main and profile.images.exists():
        new_main = profile.images.order_by('-uploaded_at').first()
        new_main.is_main = True
        new_main.save()
    context = get_profile_editor_context(request)
    return render(request, 'accounts/partials/profile_editor.html', context)

# Password Reset Views
class PasswordResetView(auth_views.PasswordResetView):
    """Custom password reset view with our template"""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    form_class = CustomPasswordResetForm
    success_url = '/accounts/password_reset/done/'

class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    """Password reset email sent confirmation"""
    template_name = 'accounts/password_reset_done.html'

class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Password reset form with new password"""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = '/accounts/password_reset/complete/'

class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    """Password reset successful confirmation"""
    template_name = 'accounts/password_reset_complete.html'



