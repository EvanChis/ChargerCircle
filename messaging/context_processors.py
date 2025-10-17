# messaging/context_processors.py

# context_processors.py might be a demon

from .models import Message

def pending_invites_count(request):
    if not request.user.is_authenticated:
        return {}
    
    # Counts messages sent to the user that are session invites
    count = Message.objects.filter(
        thread__participants=request.user,
        content__startswith='SESSION_INVITE::'
    ).exclude(
        sender=request.user
    ).count()
    
    return {'pending_invites_count': count}
