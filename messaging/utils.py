# messaging/utils.py

from django.db.models import Count
from .models import MessageThread

def get_or_create_message_thread(participants):
    
    # Helper function to find or create a message thread with a specific set of users.
    # Creates a queryset of threads that have the exact number of participants
    
    threads = MessageThread.objects.annotate(
        num_participants=Count('participants')
    ).filter(num_participants=len(participants))
    
    # Filters down to threads that contain all the specified participants - hopefully
    for participant in participants:
        threads = threads.filter(participants=participant)
        
    # If a thread is found, returns it
    if threads.exists():
        return threads.first()
        
    # If no existing thread is found, creates a new one
    thread = MessageThread.objects.create()
    thread.participants.set(participants)
    return thread
