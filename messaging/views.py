# messaging/views.py

# Import json because 'inbox_view' needs it to pass online user data to the template.
import json # for making green online dot independent so it doesn't flash

# Import render, get_object_or_404, redirect from django.shortcuts because 'inbox_view' needs them.
from django.shortcuts import render, get_object_or_404, redirect
# Import login_required from django.contrib.auth.decorators because 'inbox_view' needs it.
from django.contrib.auth.decorators import login_required
# Import MessageThread from .models because 'inbox_view' needs it to fetch chat threads and messages.
from .models import MessageThread, Message
# Import MessageForm from .forms because 'inbox_view' needs it to display the message input form.
from .forms import MessageForm
# Import get_online_user_ids from core.utils because 'inbox_view' needs it to show online status.
from core.utils import get_online_user_ids
# --- NEW IMPORTS ---
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# --- END NEW IMPORTS ---

"""
Author: Cole (Original Logic) / Oju (RT Refactor)
This function handles the main "Inbox" page where users see
their list of conversations and can chat. It shows a list of
all the user's message threads, sorted by the most recent
activity. If a specific thread ID is provided in the URL,
it loads the messages for that particular conversation.
RT: Fetches the list of currently online users to display the
green "online" dots next to chat participants. It also sets up
the necessary data for the real-time chat WebSocket connection
in the template.
"""
@login_required
def inbox_view(request, thread_id=None):
    # Get all message threads the user is part of, newest first
    my_threads = request.user.message_threads.all().order_by('-updated_at')
    
    # For each thread, find the other participants (not the logged-in user)
    for thread in my_threads:
        thread.other_participants = thread.participants.exclude(id=request.user.id)

    selected_thread = None
    messages = []
    form = MessageForm() # The form to type a new message
    
    # If a specific chat thread was clicked on
    if thread_id:
        selected_thread = get_object_or_404(MessageThread, pk=thread_id)
        # Make sure the logged-in user is actually part of this thread
        if request.user not in selected_thread.participants.all():
            return redirect('inbox') # If not, send them back to the main inbox
        
        # Find the other participants in the selected thread
        selected_thread.other_participants = selected_thread.participants.exclude(id=request.user.id)
        # Get all messages for the selected thread, oldest first
        messages = selected_thread.messages.all().order_by('timestamp')

    # Get the list of users who are currently online
    online_user_ids = get_online_user_ids() # RT: Fetches live presence data
    
    # Prepare all the data to send to the HTML template
    context = {
        'my_threads': my_threads,
        'selected_thread': selected_thread,
        'messages': messages,
        'form': form,
        'online_user_ids': online_user_ids,
        'online_user_ids_json': json.dumps(list(online_user_ids)), # RT: Passes live data for JavaScript
    }
    # Render the inbox HTML page with all the prepared data
    return render(request, 'messaging/inbox.html', context)


# Author: Angie
# View for image messages
@login_required
@require_POST
def upload_chat_image_view(request, thread_id):
    thread = get_object_or_404(MessageThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return HttpResponseForbidden()

    if 'image' in request.FILES:
        image = request.FILES['image']
        
        # Create the new message object with the image
        new_message = Message.objects.create(
            thread=thread,
            sender=request.user,
            image=image
        )
        new_message.save() # Save to get the image URL

        # --- Real-Time Broadcast ---
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{thread.id}'
        
        broadcast_data = {
            'type': 'chat_message', # Use the same type as text messages
            'message': None, # No text content
            'image_url': new_message.image.url, # Send the new image URL
            'sender_id': request.user.id,
            'sender_first_name': request.user.first_name,
        }
        
        async_to_sync(channel_layer.group_send)(room_group_name, broadcast_data)
        
        # Return a "No Content" response to tell HTMX the upload was successful
        return HttpResponse(status=204)
    
    return HttpResponse("No image provided.", status=400)
