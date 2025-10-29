# messaging/context_processors.py

from .models import Message
from .constants import SESSION_INVITE_PREFIX

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
