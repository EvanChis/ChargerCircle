# messaging/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import MessageThread
from .forms import MessageForm
from core.utils import get_online_user_ids

@login_required
def inbox_view(request, thread_id=None):
    # Gets all threads the user is a part of
    my_threads = request.user.message_threads.all().order_by('-updated_at')
    
    # Prepares the list of other participants for each thread
    for thread in my_threads:
        thread.other_participants = thread.participants.exclude(id=request.user.id)

    selected_thread = None
    messages = []
    form = MessageForm()
    
    if thread_id:
        selected_thread = get_object_or_404(MessageThread, pk=thread_id)
        if request.user not in selected_thread.participants.all():
            return redirect('inbox')
        
        # Adds other participants to the selected thread object as well
        selected_thread.other_participants = selected_thread.participants.exclude(id=request.user.id)
        messages = selected_thread.messages.all().order_by('timestamp')

    online_user_ids = get_online_user_ids()
    
    context = {
        'my_threads': my_threads,
        'selected_thread': selected_thread,
        'messages': messages,
        'form': form,
        'online_user_ids': online_user_ids,
    }
    return render(request, 'messaging/inbox.html', context)
