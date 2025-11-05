# messaging/context_processors.py

# Import Message from .models because 'pending_invites_count' needs to search the Message table.
from .models import Message
# Import SESSION_INVITE_PREFIX from .constants because 'pending_invites_count' needs it to find invite messages.
from .constants import SESSION_INVITE_PREFIX

"""
Author: Evan and Oju
This function is a "context processor," which means it runs
on almost every page load. Its job is to check the database
for any un-answered session invites for the currently logged-in
user. It returns the total count, which is then used by the
main 'base.html' template to show the red number on the
"Messages" notification badge.
RT: This function provides the data that powers the real-time
notification badge in the header.
"""
def pending_invites_count(request):
    if not request.user.is_authenticated:
        return {}
    
    # Counts session invite messages sent to the user.
    count = Message.objects.filter(
        thread__participants=request.user,
        content__startswith=SESSION_INVITE_PREFIX
    ).exclude(
        sender=request.user
    ).count()
    
    return {'pending_invites_count': count}
