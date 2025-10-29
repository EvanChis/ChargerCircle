# messaging/utils.py

# Import Count from django.db.models because 'get_or_create_message_thread' needs it to count participants.
from django.db.models import Count
# Import MessageThread from .models because 'get_or_create_message_thread' needs it to find or create threads.
from .models import MessageThread

"""
Author: Cole
This is a helper function used whenever a message needs to be
sent between a specific group of users (e.g., when two people
match, or when sending a session invite). It first checks if a
conversation thread *already* exists with exactly those people.
If it finds one, it returns it. If not, it creates a brand new
thread, adds all the people to it, and then returns the new thread.
RT: This function is often called as part of real-time actions,
like creating a chat thread immediately after a match occurs.
"""
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
