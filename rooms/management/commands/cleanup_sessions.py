# rooms/management/commands/cleanup_sessions.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from rooms.models import Session

class Command(BaseCommand):
    help = 'Deletes sessions older than 12 hours.'

    def handle(self, *args, **kwargs):
        twelve_hours_ago = timezone.now() - timedelta(hours=12)
        
        # Finds all sessions created more than 12 hours ago - maybe
        old_sessions = Session.objects.filter(created_at__lt=twelve_hours_ago)
        
        count = old_sessions.count()
        
        if count > 0:
            old_sessions.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} old session(s).'))
        else:
            self.stdout.write(self.style.SUCCESS('No old sessions to delete.'))
