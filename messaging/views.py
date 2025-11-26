# messaging/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import MessageThread, Message
from .forms import MessageForm
from core.utils import get_online_user_ids
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

@login_required
def inbox_view(request, thread_id=None):
    # Get all message threads the user is part of, newest first
    my_threads = request.user.message_threads.all().order_by('-updated_at')
    
    # For each thread, find the other participants (not the logged-in user)
    for thread in my_threads:
        thread.other_participants = thread.participants.exclude(id=request.user.id)

    selected_thread = None
    messages = []
    form = MessageForm()
    
    if thread_id:
        selected_thread = get_object_or_404(MessageThread, pk=thread_id)
        if request.user not in selected_thread.participants.all():
            return redirect('inbox') 
        
        selected_thread.other_participants = selected_thread.participants.exclude(id=request.user.id)
        messages = selected_thread.messages.all().order_by('timestamp')

    online_user_ids = get_online_user_ids()
    
    context = {
        'my_threads': my_threads,
        'selected_thread': selected_thread,
        'messages': messages,
        'form': form,
        'online_user_ids': online_user_ids,
        'online_user_ids_json': json.dumps(list(online_user_ids)),
    }
    return render(request, 'messaging/inbox.html', context)


@login_required
@require_POST
def upload_chat_image_view(request, thread_id):
    thread = get_object_or_404(MessageThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return HttpResponseForbidden()

    if 'image' in request.FILES:
        image = request.FILES['image']
        
        # Create the new message object with the image.
        # .create() automatically calls .save(), triggering your optimization logic.
        new_message = Message.objects.create(
            thread=thread,
            sender=request.user,
            image=image
        )
        # REMOVED: new_message.save() -- This was causing a double-save/optimization loop

        # --- Real-Time Broadcast ---
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{thread.id}'
        
        broadcast_data = {
            'type': 'chat_message',
            'message': None,
            'image_url': new_message.image.url,
            'sender_id': request.user.id,
            'sender_first_name': request.user.first_name,
        }
        
        async_to_sync(channel_layer.group_send)(room_group_name, broadcast_data)
        
        return HttpResponse(status=204)
    
    return HttpResponse("No image provided.", status=400)

@login_required
@require_POST
def leave_thread_view(request, thread_id):
    thread = get_object_or_404(MessageThread, pk=thread_id)
    
    if request.user in thread.participants.all():
        thread.participants.remove(request.user)
        if thread.participants.count() == 0:
            thread.delete()
        return redirect('inbox')
    
    return HttpResponseForbidden()
