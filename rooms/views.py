# rooms/views.py

import json 
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.core.management import call_command
from django.contrib.admin.views.decorators import staff_member_required


from .models import Course, Thread, Post, Session 
from messaging.models import MessageThread, Message 
from messaging.utils import get_or_create_message_thread 
from messaging.constants import SESSION_INVITE_PREFIX 
from .forms import ThreadForm, PostForm, SessionCreateForm 
from channels.layers import get_channel_layer 
from asgiref.sync import async_to_sync 
from core.utils import get_online_user_ids 

# Helper: count how many session invite messages this user has (not sent by them).
def get_pending_invites_count(user):
    return Message.objects.filter(
        thread__participants=user,
        content__startswith=SESSION_INVITE_PREFIX
    ).exclude(sender=user).count()

# Shows list of all courses except 'hang-out'
@login_required
def course_list_view(request):
    courses = Course.objects.exclude(slug='hang-out')
    return render(request, 'rooms/course_list.html', {'courses': courses})

# For maintenance
@staff_member_required
def manual_maintenance(request):
    """
    Manually triggers the event import and session cleanup commands.
    Only accessible by staff/superusers.
    """
    try:
        call_command('cleanup_sessions')
        call_command('import_events')
        return HttpResponse("Maintenance tasks complete: Sessions cleaned, Events imported.")
    except Exception as e:
        return HttpResponse(f"Error running tasks: {e}", status=500)

# Shows a single course page with threads. Also handles creating a new thread.
@login_required
def course_detail_view(request, slug):
    course = get_object_or_404(Course, slug=slug)
    # Handle form submission for creating a new thread
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            
            thread = form.save(commit=False) # Create thread object but don't save yet
            thread.course = course # Link to the current course
            thread.author = request.user # Set the author
            thread.save() # Save the new thread

            # Create the first post in the new thread
            Post.objects.create(thread=thread, content=form.cleaned_data['content'], author=request.user)
            
            # --- Real-Time Broadcast ---
            # Build HTML for the new thread item
            channel_layer = get_channel_layer()
            html = render_to_string("rooms/partials/thread_item.html", {'thread': thread, 'course': course})
            # Send the HTML to everyone in the course room's WebSocket group
            async_to_sync(channel_layer.group_send)(
                f'course_room_{course.slug}',
                {
                    'type': 'broadcast_message', # The type of message for the consumer
                    'html': html, # The HTML content to broadcast
                    'message_type': 'new_thread' # Specific type for client-side JS
                }
            )
            # --- End Real-Time ---
            
            # Redirect user to the new thread's detail page
            return redirect('thread_detail', slug=course.slug, pk=thread.pk)
    
    # If not POST, just display the page
    threads = course.threads.all() # Get all threads for this course
    form = ThreadForm() # Create an empty form for starting a new thread
    context = { 'course': course, 'threads': threads, 'form': form, }
    return render(request, 'rooms/course_detail.html', context)

# Shows a thread page, lists posts, and handles replies
@login_required
def thread_detail_view(request, slug, pk):
    thread = get_object_or_404(Thread, pk=pk, course__slug=slug)
    posts = thread.posts.order_by('created_at') # Get all posts, oldest first
    original_post = posts.first() # The very first post
    replies = posts[1:] # All other posts are replies
    
    # Handle form submission for posting a reply
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False) # Create post object but don't save yet
            post.thread = thread # Link to the current thread
            post.author = request.user # Set the author
            post.save() # Save the new reply

            # --- Real-Time Broadcast ---
            # broadcasts new post to course group (live update)
            channel_layer = get_channel_layer()
            html = render_to_string("rooms/partials/post_item.html", {'post': post})
            # Send the HTML to everyone in the course room's WebSocket group
            async_to_sync(channel_layer.group_send)(
                f'course_room_{slug}', # Use the course slug for the group name
                {
                    'type': 'broadcast_message', # Message type for the consumer
                    'html': html, # HTML content to broadcast
                    'message_type': 'new_post' # Specific type for client-side JS
                }
            )
            # --- End Real-Time ---
            # Redirect back to the same thread page (to clear the form)
            return redirect('thread_detail', slug=slug, pk=pk)
            
    # If not POST, just display the page
    form = PostForm() # Create an empty form for posting a reply
    context = { 'thread': thread, 'original_post': original_post, 'replies': replies, 'form': form, }
    return render(request, 'rooms/thread_detail.html', context)

# Edits a post
@login_required
def edit_post_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    # Security check: only the author can edit
    if request.user != post.author: return HttpResponseForbidden()
    
    # Handle form submission
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post) # Load form with submitted data and existing post
        if form.is_valid():
            form.save() # Save the changes
            # Return the updated HTML for the post item
            # RT: Returns HTML partial for HTMX swap
            return render(request, 'rooms/partials/post_item.html', {'post': post})
    else: # Handle initial request to show the edit form
        form = PostForm(instance=post) # Load form with existing post data
        # Return the HTML for the edit form itself
        # RT: Returns HTML partial for HTMX swap
        return render(request, 'rooms/partials/edit_post_form.html', {'form': form, 'post': post})

# Deletes a post
@login_required
@require_POST # Ensure this view only accepts POST requests
def delete_post_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    # Security check: only the author can delete
    if request.user != post.author: return HttpResponseForbidden()
    
    # Check if this is the last post in the thread
    if post.thread.posts.count() == 1:
        thread = post.thread
        course = thread.course
        thread.delete() # Delete the entire thread
        # RT: Redirects the user via HTMX header after deleting the thread
        response = HttpResponse('')
        response['HX-Redirect'] = redirect('course_detail', slug=course.slug).url
        return response
        
    # If not the last post, just delete the post
    post.delete()
    # RT: Returns empty response for HTMX to delete the post item
    return HttpResponse('')

# Creates a live Session. Also sends invite messages to selected buddies.
@login_required
def create_session_view(request):
    # Handle form submission
    if request.method == 'POST':
        form = SessionCreateForm(request.POST, user=request.user) # Pass the user to the form
        if form.is_valid():
            session = form.save(commit=False) # Create session object but don't save yet
            session.host = request.user # Set the host
            session.save() # Save the new session
            session.participants.add(request.user) # Add the host as a participant
            
            invited_buddies = form.cleaned_data.get('buddies_to_invite')
            all_participants = [request.user] + list(invited_buddies)
            # Find or create a group chat thread for everyone involved
            thread = get_or_create_message_thread(all_participants)
            
            # --- NAME THE THREAD FOR THE SESSION ---
            thread.name = f"Session: {session.topic}"
            thread.save()
            # ---------------------------------------
            
            # --- Create Invite Message ---
            # Uses the constant to build the invite string
            invite_content = f"{SESSION_INVITE_PREFIX}{session.id}::{request.user.first_name} invited you to a session for {session.course.name} on the topic: {session.topic}"
            new_message = Message.objects.create(thread=thread, sender=request.user, content=invite_content)
            thread.save()  # Update thread's timestamp for sorting
            # --- End Invite Message ---
            
            # --- Real-Time Broadcasts ---
            # Sends the invite message into the chat thread real-time
            channel_layer = get_channel_layer()
            room_group_name = f'chat_{thread.id}'
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'chat_message', # Message type for the chat consumer
                    'message': new_message.content,
                    'sender_id': request.user.id,
                    'sender_first_name': request.user.first_name,
                }
            )
            
            # Sends a small notification to each invited buddy for notification badge
            for buddy in invited_buddies:
                group_name = f'notifications_for_user_{buddy.pk}'
                # Get the updated count *after* the new invite is created
                updated_invite_count = get_pending_invites_count(buddy)
                message = {
                    'type': 'send_notification', # Message type for the notification consumer
                    'message': {
                        'text': f'{request.user.first_name} invited you to a new session!',
                        'invite_count': updated_invite_count # Send the correct count
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, message)
            # --- End Real-Time ---

            # Redirect the user to the chat thread where the invite was sent
            return redirect('conversation', thread_id=thread.pk)
    else: # Handle initial request to show the form
        form = SessionCreateForm(user=request.user) # Pass the user to the form
    return render(request, 'rooms/create_session.html', {'form': form})

# Accepts an invite: adds user to session and updates the invite message
@login_required
@require_POST
def accept_session_invite(request, session_id, message_id):
    session = get_object_or_404(Session, pk=session_id)
    message = get_object_or_404(Message, pk=message_id)
    session.participants.add(request.user) # Add user to the session
    # Update the message content
    message.content = f"{request.user.first_name} accepted the invite."
    message.save()

    # --- Real-Time Badge Update ---
    # updates the user's notification badge real-time
    channel_layer = get_channel_layer()
    group_name = f'notifications_for_user_{request.user.pk}'
    # Get the count *after* accepting (should decrease)
    updated_invite_count = get_pending_invites_count(request.user)
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification', # Message type for notification consumer
            'message': {'invite_count': updated_invite_count} # Send updated count
        }
    )
    # --- End Real-Time ---
    
    # RT: Return the updated HTML content for the message bubble via HTMX
    return render(request, 'messaging/partials/message_content.html', {'message': message})

# Declines an invite: updates message and notifies user
@login_required
@require_POST
def decline_session_invite(request, session_id, message_id):
    message = get_object_or_404(Message, pk=message_id)
    # Update the message content
    message.content = f"{request.user.first_name} declined the invite."
    message.save()
    
    # --- Real-Time Badge Update ---
    channel_layer = get_channel_layer()
    group_name = f'notifications_for_user_{request.user.pk}'
    # Get the count *after* declining (should decrease)
    updated_invite_count = get_pending_invites_count(request.user)
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification', # Message type for notification consumer
            'message': {'invite_count': updated_invite_count} # Send updated count
        }
    )
    # --- End Real-Time ---
    
    # RT: Return the updated HTML content for the message bubble via HTMX
    return render(request, 'messaging/partials/message_content.html', {'message': message})

# Shows the session page
@login_required
def session_detail_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    # Security check: only participants can view
    if request.user not in session.participants.all():
        return HttpResponseForbidden("You are not a participant of this session.")
        
    # Get online users for the green dots
    online_user_ids = get_online_user_ids() # RT: Fetches live presence data
    context = {
        'session': session,
        'online_user_ids': online_user_ids,
        'online_user_ids_json': json.dumps(list(online_user_ids)), # RT: Passes live data for JS
    }
    return render(request, 'rooms/session_detail.html', context)

# Deletes a session
@login_required
@require_POST
def delete_session_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    # Security check: only the host can delete
    if request.user != session.host:
        return HttpResponseForbidden()
    session.delete()
    return redirect('sessions') # Redirect to the main sessions list page

# Leaves a session
@login_required
@require_POST
def leave_session_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    # Remove the current user from the participants
    session.participants.remove(request.user)
    return redirect('sessions') # Redirect to the main sessions list page

# Returns a small HTML snippet listing participants
@login_required
def session_participants_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    # Security check: only participants should access this
    if request.user not in session.participants.all():
        return HttpResponseForbidden()
        
    # Get online users for the green dots
    online_user_ids = get_online_user_ids() # RT: Fetches live presence data
    context = {'session': session, 'online_user_ids': online_user_ids}
    # RT: Return only the HTML partial for the participant list via HTMX
    return render(request, 'rooms/partials/participant_list.html', context)
