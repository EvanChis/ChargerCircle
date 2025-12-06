# accounts/views.py

import json
import os
import requests # For Resend API

# Import render, redirect, get_object_or_404 from django.shortcuts because almost all views need them.
from django.shortcuts import render, redirect, get_object_or_404
# Import login, logout, get_user_model from django.contrib.auth because 'signup_view', 'logout_view', and many views need them.
from django.contrib.auth import login, logout, get_user_model
# Import login_required from django.contrib.auth.decorators because most views in this file need it.
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
# Import HttpResponse from django.http because 'remove_buddy', 'undo_action_view' need it.
from django.http import HttpResponse
# Import models from django.db because 'buddies_view' needs Q for complex queries.
from django.db import models
# Import require_POST from django.views.decorators.http because several views need it.
from django.views.decorators.http import require_POST
# Import async_to_sync from asgiref.sync because 'check_for_match' needs it.
from asgiref.sync import async_to_sync
# Import get_channel_layer from channels.layers because 'check_for_match' needs it.
from channels.layers import get_channel_layer
# Import render_to_string from django.template.loader because (it's needed to turn HTML templates into strings).
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator


# Import CustomUserCreationForm, ProfileImageForm, ProfileUpdateForm from .forms because 'signup_view' and 'edit_profile_view' need them.
from .forms import CustomUserCreationForm, ProfileImageForm, ProfileUpdateForm, CustomPasswordResetForm
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
    
    # Check if user has any buddies left
    buddy_list = request.user.buddies.all()
    
    if buddy_list.exists():
        # RT: Returns an empty response for HTMX to delete the item
        return HttpResponse('')
    else:
        # RT: If no buddies left, return the empty state and hide the search/filter UI with out-of-band swaps
        empty_state_html = render_to_string('accounts/partials/buddy_list_empty.html', request=request)
        response_html = f'''
            <div hx-swap-oob="innerHTML:#buddy-list-container">{empty_state_html}</div>
            <div hx-swap-oob="innerHTML:#buddy-search-filter-wrapper"></div>
        '''
        return HttpResponse(response_html)

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
Author: Oju
This function loads the "Buddies" page. It gathers the user's
buddy list and their recent actions that can be undone.
RT: Fetches the list of currently online users to display the
green "online" dots next to buddies.
"""
@login_required
def buddies_view(request):
    buddy_list = request.user.buddies.all()
    
    # Get filter and search parameters
    search_query = request.GET.get('search', '').strip()
    online_filter = request.GET.get('online', '')
    course_filter = request.GET.get('course', '')
    sort_by = request.GET.get('sort', '')
    
    # Apply search filter (by name)
    if search_query:
        buddy_list = buddy_list.filter(
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query)
        )
    
    # Apply online status filter
    online_user_ids = get_online_user_ids() # RT: Fetches live presence data
    if online_filter == 'online':
        buddy_list = buddy_list.filter(pk__in=online_user_ids)
    elif online_filter == 'offline':
        buddy_list = buddy_list.exclude(pk__in=online_user_ids)
    
    # Apply course filter
    if course_filter:
        buddy_list = buddy_list.filter(courses__slug=course_filter)
    
    # Apply sorting
    if sort_by == 'name_asc':
        buddy_list = buddy_list.order_by('first_name', 'last_name')
    elif sort_by == 'name_desc':
        buddy_list = buddy_list.order_by('-first_name', '-last_name')
    
    # Get user's courses for filter dropdown
    from rooms.models import Course
    user_courses = Course.objects.filter(students=request.user).exclude(slug='hang-out')
    
    # Get or create message threads for each buddy (simple approach)
    for buddy in buddy_list:
        buddy.message_thread = get_or_create_message_thread([request.user, buddy])
    
    last_skipped = SkippedMatch.objects.filter(from_user=request.user)[:10]

    # Check if any filters are active
    has_filters = bool(search_query or online_filter or course_filter or sort_by)
    
    context = {
        'buddy_list': buddy_list,
        'online_user_ids': online_user_ids,
        'last_skipped': last_skipped,
        'online_user_ids_json': json.dumps(list(online_user_ids)), # RT: Passes live data to the page
        'user_courses': user_courses,
        'search_query': search_query,
        'online_filter': online_filter,
        'course_filter': course_filter,
        'sort_by': sort_by,
        'has_filters': has_filters,
    }
    
    # If this is an HTMX request, return only the buddy list partial
    if request.headers.get('HX-Request'):
        if buddy_list:
            return render(request, 'accounts/partials/buddy_list.html', context)
        else:
            # If filters are active but no results, show "no results" message
            # Otherwise show the empty state
            if has_filters:
                return render(request, 'accounts/partials/buddy_list_no_results.html', context)
            else:
                return render(request, 'accounts/partials/buddy_list_empty.html', context)
    
    return render(request, 'accounts/buddies.html', context)


"""
Author: Evan
This function just shows the main dashboard page after a
user logs in.
"""
@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

# --- EMAIL VERIFICATION HELPERS ---

def send_verification_email(user, request):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verify_url = request.build_absolute_uri(reverse('verify_email', kwargs={'uidb64': uid, 'token': token}))
    
    resend_api_key = os.environ.get('EMAIL_API_KEY')
    if not resend_api_key:
        print("ERROR: EMAIL_API_KEY not set.")
        return

    subject = "Verify your Charger Circle email"
    html_content = f"""
    <h2>Welcome to Charger Circle!</h2>
    <p>Please click the link below to verify your @uah.edu email address and activate your account:</p>
    <p><a href="{verify_url}">Verify Email</a></p>
    <p>If you didn't sign up, you can ignore this email.</p>
    """

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            json={
                "from": "Charger Circle <noreply@mail.girlstanding.app>", # Or your verified domain
                "to": [user.email],
                "subject": subject,
                "html": html_content
            },
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending verification email: {e}")

# --- UPDATED SIGNUP & VERIFY VIEWS ---

"""
Author: Evan
This function handles the user sign-up page. It shows the
form to a new user and, when they submit it, it creates
their account, sets it to inactive, sends a verification email,
and shows a confirmation page.
"""
def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False # Deactivate until verified
            user.save()
            
            try:
                # Get ALL hidden tags
                hidden_tags = Course.objects.filter(tag_type='hidden')
                user.courses.add(*hidden_tags)
            except Course.DoesNotExist:
                pass
            
            # Send Email
            send_verification_email(user, request)
            
            return render(request, 'accounts/verification_sent.html')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, "Email verified! Welcome to Charger Circle.")
        return redirect('dashboard')
    else:
        return HttpResponse('Activation link is invalid!', status=400)

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
Author: Oju
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
        'match_age_min': profile.match_age_min,
        'match_age_max': profile.match_age_max,
        # Pass both interests and courses to the form initial data
        'interests': request.user.courses.filter(tag_type='interest'),
        'courses': request.user.courses.filter(tag_type='course'),
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
                profile.match_age_min = update_form.cleaned_data['match_age_min']
                profile.match_age_max = update_form.cleaned_data['match_age_max']
                profile.save()
                
                # Get all tag sets
                interests = update_form.cleaned_data['interests']
                courses = update_form.cleaned_data['courses']
                # We must preserve existing hidden tags (like hang-out)
                hidden_tags = user.courses.filter(tag_type='hidden')
                
                # Set the user's courses to the combination of all three
                user.courses.set(interests | courses | hidden_tags)
                
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

"""
Author: Evan
This function permanently deletes the user's account. It is a
destructive action that removes all user data. It logs the user
out first to ensure a clean session termination.
"""
@login_required
@require_POST
def delete_account_view(request):
    # Permanently delete the user account
    user = request.user
    logout(request)
    user.delete()
    return redirect('home')

# Password Reset Views
class PasswordResetView(auth_views.PasswordResetView):
    """Custom password reset view with our template"""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    html_email_template_name = 'accounts/password_reset_email.html'
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

