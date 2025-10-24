# accounts/views.py

import json # for making green online dot independent so it doesn't flash

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.template.loader import render_to_string


from .forms import CustomUserCreationForm, ProfileImageForm, ProfileUpdateForm
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

        # Cleans up the corresponding SkippedMatch "like" entries
        SkippedMatch.objects.filter(from_user=user1, skipped_user=user2, action_type='like').delete()
        SkippedMatch.objects.filter(from_user=user2, skipped_user=user1, action_type='like').delete()
        
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
        # Create a Like object and an undoable action
        Like.objects.get_or_create(from_user=request.user, to_user=liked_user)
        # prevents duplicates if user skips then likes
        SkippedMatch.objects.update_or_create(
            from_user=request.user, 
            skipped_user=liked_user, 
            defaults={'action_type': 'like'}
        )
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
    
    # This is now a permanent removal
    request.user.buddies.remove(buddy_to_remove)
    buddy_to_remove.buddies.remove(request.user)
    
    # SkippedMatch entries are created to prevent them from seeing each other again.
    SkippedMatch.objects.get_or_create(from_user=request.user, skipped_user=buddy_to_remove)
    SkippedMatch.objects.get_or_create(from_user=buddy_to_remove, skipped_user=request.user)
    
    # We return an empty response because the item is now gone permanently.
    return HttpResponse('')

@login_required
@require_POST
def undo_action_view(request, pk):
    # This view now handles both "likes" and "skips"
    action_to_undo = get_object_or_404(SkippedMatch, pk=pk, from_user=request.user)
    
    if action_to_undo.action_type == 'like':
        # If it was a "like", we delete the corresponding Like object.
        Like.objects.filter(from_user=request.user, to_user=action_to_undo.skipped_user).delete()
    
    # For both likes and skips, we delete the SkippedMatch record.
    action_to_undo.delete()

    return HttpResponse('')

@login_required
def buddies_view(request):
    buddy_list = request.user.buddies.all()
    online_user_ids = get_online_user_ids()
    last_skipped = SkippedMatch.objects.filter(from_user=request.user)[:10]

    context = {
        'buddy_list': buddy_list,
        'online_user_ids': online_user_ids,
        'last_skipped': last_skipped,
        'online_user_ids_json': json.dumps(list(online_user_ids)),
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
    # handles case where user likes then skips
    SkippedMatch.objects.update_or_create(
        from_user=request.user, 
        skipped_user=skipped_user,
        defaults={'action_type': 'skip'}
    )
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
