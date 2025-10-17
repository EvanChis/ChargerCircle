# accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .forms import CustomUserCreationForm, ProfileImageForm, ProfileUpdateForm
from .services import find_matches
from .models import BuddyRequest, ProfileImage, SkippedMatch
from rooms.models import Course, Session
from messaging.utils import get_or_create_message_thread
from core.utils import get_online_user_ids

User = get_user_model()

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
@require_POST
def send_buddy_request(request, pk):
    to_user = get_object_or_404(User, pk=pk)
    SkippedMatch.objects.get_or_create(from_user=request.user, skipped_user=to_user)
    if to_user != request.user:
        BuddyRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
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
def buddies_view(request):
    incoming_buddy_requests = BuddyRequest.objects.filter(to_user=request.user)
    buddy_list = request.user.buddies.all()
    online_user_ids = get_online_user_ids()
    context = {
        'incoming_buddy_requests': incoming_buddy_requests,
        'buddy_list': buddy_list,
        'online_user_ids': online_user_ids,
    }
    return render(request, 'accounts/buddies.html', context)

@login_required
@require_POST
def accept_buddy_request(request, request_id):
    buddy_request = get_object_or_404(BuddyRequest, id=request_id, to_user=request.user)
    request.user.buddies.add(buddy_request.from_user)
    buddy_request.from_user.buddies.add(request.user)
    get_or_create_message_thread([request.user, buddy_request.from_user])
    channel_layer = get_channel_layer()
    group_name = f'notifications_for_user_{buddy_request.from_user.pk}'
    message = { 'type': 'send_notification', 'message': { 'text': f'{request.user.first_name} accepted your buddy request!' } }
    async_to_sync(channel_layer.group_send)(group_name, message)
    buddy_request.delete()
    buddy_list = request.user.buddies.all()
    online_user_ids = get_online_user_ids()
    context = { 'buddy_list': buddy_list, 'online_user_ids': online_user_ids, }
    return render(request, 'accounts/partials/buddy_request_accepted.html', context)

@login_required
@require_POST
def decline_buddy_request(request, request_id):
    buddy_request = get_object_or_404(BuddyRequest, id=request_id, to_user=request.user)
    buddy_request.delete()
    return HttpResponse('')

@login_required
@require_POST
def remove_buddy(request, pk):
    buddy_to_remove = get_object_or_404(User, pk=pk)
    request.user.buddies.remove(buddy_to_remove)
    buddy_to_remove.buddies.remove(request.user)
    return HttpResponse('')

@login_required
def profile_view(request, pk=None):
    if pk:
        profile_user = get_object_or_404(User, pk=pk)
    else:
        profile_user = request.user
    thread = None
    if profile_user != request.user:
        thread = get_or_create_message_thread([request.user, profile_user])
    
    # This is the fix for the empty pictures bug
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
    update_form = ProfileUpdateForm(initial={
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'age': request.user.age,
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
                update_form.save()
                profile.bio = update_form.cleaned_data['bio']
                profile.save()
                request.user.courses.set(update_form.cleaned_data['courses'])
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
