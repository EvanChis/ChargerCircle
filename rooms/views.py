# rooms/views.py

# Import json because 'session_detail_view' needs it to pass online user data.
import json # for making green online dot independent so it doesn't flash

# Import render, get_object_or_404, redirect from django.shortcuts because most views need them.
from django.shortcuts import render, get_object_or_404, redirect
# Import login_required from django.contrib.auth.decorators because most views need it.
from django.contrib.auth.decorators import login_required
# Import render_to_string from django.template.loader because 'course_detail_view', 'thread_detail_view' need it.
from django.template.loader import render_to_string
# Import HttpResponse, HttpResponseForbidden from django.http because several views need them.
from django.http import HttpResponse, HttpResponseForbidden
# Import require_POST from django.views.decorators.http because several views need it.
from django.views.decorators.http import require_POST
# Import Count from django.db.models because 'get_pending_invites_count' needs it (though not directly used here, maybe previously).
from django.db.models import Count

# Import models from .models because Course, Thread, Post, Session are needed by most views.
from .models import Course, Thread, Post, Session # models
# Import MessageThread, Message from messaging.models because 'create_session_view', 'accept_session_invite', 'decline_session_invite' need them.
from messaging.models import MessageThread, Message # messaging app models because session invites
# Import get_or_create_message_thread from messaging.utils because 'create_session_view' needs it.
from messaging.utils import get_or_create_message_thread # session invites
# Import SESSION_INVITE_PREFIX from messaging.constants because 'create_session_view', 'get_pending_invites_count' need it.
from messaging.constants import SESSION_INVITE_PREFIX # working on it - prefix used for invite messages
# Import forms from .forms because ThreadForm, PostForm, SessionCreateForm are needed by several views.
from .forms import ThreadForm, PostForm, SessionCreateForm # forms for creating threads/posts/sessions
# Import get_channel_layer from channels.layers because several views need it to send real-time messages.
from channels.layers import get_channel_layer # for real-time websocket messaging
# Import async_to_sync from asgiref.sync because several views need it to call async channel layer functions.
from asgiref.sync import async_to_sync # lets sync code call async functions
# Import get_online_user_ids from core.utils because 'session_detail_view', 'session_participants_view' need it.
from core.utils import get_online_user_ids # helper to check who is online

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This helper function counts how many pending session invites
a user has received but not yet responded to.
RT: This count is used to update the real-time notification badge.
"""
# Helper: count how many session invite messages this user has (not sent by them).
def get_pending_invites_count(user):
    return Message.objects.filter(
        thread__participants=user,
        content__startswith='SESSION_INVITE::' # invite messages start with this text
    ).exclude(sender=user).count() # doesn't count invites the user sent themself

"""
Author: Angie
This function displays the main page listing all available
course rooms, excluding the general 'hang-out' room.
"""
# Shows list of all courses except 'hang-out'
@login_required
def course_list_view(request):
    courses = Course.objects.exclude(slug='hang-out')
    return render(request, 'rooms/course_list.html', {'courses': courses})

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function displays the page for a single course room. It shows
the list of discussion threads within that room and includes a form
to start a new thread. When a new thread is submitted, it saves it
and the initial post.
RT: After saving a new thread, it broadcasts the HTML for the new
thread item via WebSocket so it appears instantly for other users
in the same room.
"""
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

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function displays the page for a single discussion thread.
It shows the original post and all subsequent replies. It also
includes a form for users to add their own reply.
RT: When a new reply is submitted and saved, it broadcasts the
HTML for the new post via WebSocket so it appears instantly for
other users viewing the same thread (within the same course room).
"""
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

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function handles editing an existing post. When requested
via GET, it returns the HTML form pre-filled with the post's
content. When the form is submitted via POST, it saves the
changes and returns the updated HTML for just that post item.
RT: This view is designed to work with HTMX. It receives GET
requests from HTMX to show the edit form, and POST requests
to save changes, returning HTML partials in both cases.
"""
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

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function handles deleting a post. It includes a special
check: if the post being deleted is the *only* post in a thread,
it deletes the entire thread instead. Otherwise, it just deletes
the single post.
RT: This view is triggered by an HTMX POST request. It returns an
empty response, which HTMX interprets as "delete the element
that triggered this request" (the post item). If the whole thread
is deleted, it uses a special HTMX header to redirect the user.
"""
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
        # return redirect('course_detail', slug=course.slug) # Redirect to the course page
        
    # If not the last post, just delete the post
    post.delete()
    # RT: Returns empty response for HTMX to delete the post item
    return HttpResponse('')

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function handles the creation of a new live study session.
It displays the form on GET and processes it on POST. When a
session is created, it adds the host as a participant, finds or
creates a message thread for all invited participants, creates a
special "invite" message, and sends it.
RT: After creating the invite message, it broadcasts the message
content to the relevant chat thread via WebSocket. It also sends
a separate, smaller notification to each invited buddy via WebSocket
to update their notification badge count in real-time.
"""
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
            
            # --- Create Invite Message ---
            # Uses the constant to build the invite string
            invite_content = f"{SESSION_INVITE_PREFIX}{session.id}::{request.user.first_name} invited you to a session for {session.course.name} on the topic: {session.topic}"
            new_message = Message.objects.create(thread=thread, sender=request.user, content=invite_content)
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

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function handles a user clicking "Accept" on a session
invite within the chat. It adds the user to the session's
participants, updates the original invite message to show it
was accepted, and sends a notification to update the user's
own notification badge count (as the invite is no longer pending).
RT: This is triggered by an HTMX POST request. It returns the
updated HTML content for the message bubble. It also sends a
real-time WebSocket notification to update the user's badge count.
"""
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

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function handles a user clicking "Decline" on a session
invite within the chat. It updates the original invite message
to show it was declined and sends a notification to update the
user's own notification badge count (as the invite is no longer pending).
RT: This is triggered by an HTMX POST request. It returns the
updated HTML content for the message bubble. It also sends a
real-time WebSocket notification to update the user's badge count.
"""
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

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function displays the detail page for a specific live session.
It shows the session topic, host, and the list of participants.
RT: It fetches the list of currently online users to display the
green "online" dots next to participants. The participant list
itself is designed to auto-refresh using HTMX polling.
"""
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

"""
Author: Angie
This function allows the host of a session to delete it.
It performs a security check to ensure only the host can
delete, then removes the session from the database and
redirects the user back to their main sessions list.
"""
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

"""
Author: Angie
This function allows a participant (who is not the host) to
leave a session. It removes the user from the session's
participant list and redirects them back to their main
sessions list.
"""
# Leaves a session
@login_required
@require_POST
def leave_session_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    # Remove the current user from the participants
    session.participants.remove(request.user)
    return redirect('sessions') # Redirect to the main sessions list page

"""
Author: Angie (Original Logic) / Oju (RT Refactor)
This function returns just the HTML fragment for the list
of participants in a session. It's used by the session detail
page for periodic updates.
RT: This view is specifically designed to be called repeatedly
by HTMX (using `hx-trigger="every 5s"`) to provide a live-updating
participant list with correct online statuses.
"""
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
