# accounts/views.py

import json # Import json because 'buddies_view' needs it to pass online user data.

# Import render, redirect, get_object_or_404 from django.shortcuts because almost all views need them.
from django.shortcuts import render, redirect, get_object_or_404
# Import login, logout, get_user_model from django.contrib.auth because 'signup_view', 'logout_view', and many views need them.
from django.contrib.auth import login, logout, get_user_model
# Import login_required from django.contrib.auth.decorators because most views in this file need it.
from django.contrib.auth.decorators import login_required
# Import HttpResponse from django.http because 'remove_buddy', 'undo_action_view' need it.
from django.http import HttpResponse
# Import require_POST from django.views.decorators.http because several views need it.
from django.views.decorators.http import require_POST
# Import async_to_sync from asgiref.sync because 'check_for_match' needs it.
from asgiref.sync import async_to_sync
# Import get_channel_layer from channels.layers because 'check_for_match' needs it.
from channels.layers import get_channel_layer
# Import render_to_string from django.template.loader because (it's needed to turn HTML templates into strings).
from django.template.loader import render_to_string


# Import CustomUserCreationForm, ProfileImageForm, ProfileUpdateForm from .forms because 'signup_view' and 'edit_profile_view' need them.
from .forms import CustomUserCreationForm, ProfileImageForm, ProfileUpdateForm
# Import find_matches from .services because 'like_user_view', 'discover_view', 'skip_match_view' need it.
from .services import find_matches
# Import ProfileImage, SkippedMatch, Like from .models because many views need them.
from .models import ProfileImage, SkippedMatch, Like
# Import Course, Session from rooms.models because 'signup_view' and 'sessions_view' need them.
from rooms.models import Course, Session
# Import get_or_create_message_thread from messaging.utils because 'check_for_match' and 'profile_view' need them.
from messaging.utils import get_or_create_message_thread
# Import get_online_user_ids from core.utils because 'buddies_view' needs it.
from core.utils import get_online_user_ids

User = get_user_model()

"""
Author: Evan
This is a helper function that runs when two users have both
liked each other. It automatically creates a "buddy" connection,
starts a new private message thread for them, and cleans up
the old "Like" records.
RT: Sends a real-time "You matched!" notification to both users.
"""
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
        async_to_sync(channel_layer.group_send)(group_name_1, message_1) # RT: Pushes a live notification
        
        group_name_2 = f'notifications_for_user_{user2.pk}'
        message_2 = { 'type': 'send_notification', 'message': { 'text': f'You matched with {user1.first_name}!' } }
        async_to_sync(channel_layer.group_send)(group_name_2, message_2) # RT: Pushes a live notification

        return True
    return False


"""
Author: Evan
This function is called when a user clicks "Like" on the Discover
page. It saves the "like" and then checks if it's a mutual match.
RT: This is triggered by an HTMX request and responds by sending back
the HTML for the *next* user card to display.
"""
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
        # RT: This sends back an HTML partial for HTMX to swap
        return render(request, 'accounts/partials/match_card.html', {'match': next_match})
    else:
        # RT: This sends back an HTML partial for HTMX to swap
        return render(request, 'accounts/partials/no_more_matches.html')

"""
Author: Evan
This function is called when a user clicks the "Remove" button
on their buddy list. It permanently removes the buddy connection
and prevents them from being matched again.
RT: This is triggered by an HTMX request. It returns an empty
response, which HTMX uses to remove the item from the list.
"""
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
    
    # RT: Returns an empty response for HTMX to delete the item
    return HttpResponse('')

"""
Author: Evan
This function is called when a user clicks the "Undo" button
on the Buddies page. It finds the "skip" or "like" action and
deletes it, allowing that user to show up in Discover again.
RT: This is triggered by an HTMX request. It returns an empty
response, which HTMX uses to remove the item from the list.
"""
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

    # RT: Returns an empty response for HTMX to delete the item
    return HttpResponse('')

"""
Author: Evan
This function loads the "Buddies" page. It gathers the user's
buddy list and their recent actions that can be undone.
RT: Fetches the list of currently online users to display the
green "online" dots next to buddies.
"""
@login_required
def buddies_view(request):
    buddy_list = request.user.buddies.all()
    online_user_ids = get_online_user_ids() # RT: Fetches live presence data
    last_skipped = SkippedMatch.objects.filter(from_user=request.user)[:10]

    context = {
        'buddy_list': buddy_list,
        'online_user_ids': online_user_ids,
        'last_skipped': last_skipped,
        'online_user_ids_json': json.dumps(list(online_user_ids)), # RT: Passes live data to the page
    }
    return render(request, 'accounts/buddies.html', context)


"""
Author: Evan
This function just shows the main dashboard page after a
user logs in.
"""
@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

"""
Author: Evan
This function handles the user sign-up page. It shows the
form to a new user and, when they submit it, it creates
their account, logs them in, and sends them to the dashboard.
"""
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

"""
Author: Evan
This function logs the user out of the application and sends
them back to the public home page.
"""
def logout_view(request):
    logout(request)
    return redirect('home')

"""
Author: Evan
This function shows the "Discover" page, which is where
users can find new buddies. It finds the first available
person for the user to see and displays their card.
"""
@login_required
def discover_view(request):
    matches = find_matches(request.user)
    next_match = matches[0] if matches else None
    context = {'match': next_match}
    return render(request, 'accounts/discover.html', context)

"""
Author: Evan
This function is called when a user clicks "Skip" on the Discover
page. It records the skip so the user isn't shown again.
RT: This is triggered by an HTMX request and responds by sending back
the HTML for the *next* user card to display.
"""
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
        # RT: This sends back an HTML partial for HTMX to swap
        return render(request, 'accounts/partials/match_card.html', {'match': next_match})
    else:
        # RT: This sends back an HTML partial for HTMX to swap
        return render(request, 'accounts/partials/no_more_matches.html')

"""
Author: Evan
This function shows the "Your Sessions" page, which lists
all the study sessions the user has joined.
"""
@login_required
def sessions_view(request):
    my_sessions = Session.objects.filter(participants=request.user)
    context = {'my_sessions': my_sessions}
    return render(request, 'accounts/sessions.html', context)

"""
Author: Evan
This function shows a user's profile page. It can either show
the logged-in user's *own* profile (if no ID is given) or
show another user's public profile. If it's another user,
it also finds or creates the private message thread
between them.
"""
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

"""
Author: Evan
This is a helper function that just gathers all the necessary
information needed to display the profile editing forms, like
the image upload form and the bio/courses form.
"""
def get_profile_editor_context(request):
    profile = request.user.profile
    image_form = ProfileImageForm()
    profile_images = profile.images.order_by('-is_main', '-uploaded_at')
    update_form = ProfileUpdateForm(instance=request.user, initial={
        'bio': profile.bio,
        'courses': request.user.courses.all(),
    })
    return {'image_form': image_form, 'update_form': update_form, 'profile_images': profile_images}

"""
Author: Evan
This function handles the "Edit Profile" page. It does two
things:
1. It handles the normal (non-RT) form submission for saving
   changes to the user's bio and course list.
2. It handles the image upload.
RT: When a user selects a picture, it's uploaded via an HTMX
request, and this function sends back the updated
HTML for the image gallery.
"""
@login_required
def edit_profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        if 'image' in request.FILES: # This is the RT (HTMX) part
            image_form = ProfileImageForm(request.POST, request.FILES)
            if image_form.is_valid() and profile.images.count() < 5:
                profile_image = image_form.save(commit=False)
                profile_image.profile = profile
                if profile.images.count() == 0:
                    profile_image.is_main = True
                profile_image.save()
            context = get_profile_editor_context(request)
            # RT: This sends back an HTML partial for HTMX to swap
            return render(request, 'accounts/partials/profile_editor.html', context)
        else: # This is the standard (non-RT) form part
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

"""
Author: Evan
This function is called when a user clicks "Set as Main" on
one of their profile pictures. It updates which photo is
their main one.
RT: This is triggered by an HTMX request and sends back the
refreshed HTML for the entire image gallery.
"""
@login_required
@require_POST
def set_main_profile_image(request, pk):
    profile = request.user.profile
    image = get_object_or_404(ProfileImage, pk=pk, profile=profile)
    profile.images.update(is_main=False)
    image.is_main = True
    image.save()
    context = get_profile_editor_context(request)
    # RT: This sends back an HTML partial for HTMX to swap
    return render(request, 'accounts/partials/profile_editor.html', context)

"""
Author: Evan
This function is called when a user clicks "Delete" on
one of their profile pictures. It deletes the photo and,
if needed, sets a new "main" photo.
RT: This is triggered by an HTMX request and sends back the
refreshed HTML for the entire image gallery.
"""
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
    # RT: This sends back an HTML partial for HTMX to swap
    return render(request, 'accounts/partials/profile_editor.html', context)
