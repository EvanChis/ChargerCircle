# rooms/management/commands/cleanup_sessions.py

# Import BaseCommand from django.core.management.base because custom management commands are based on it.
from django.core.management.base import BaseCommand
# Import timezone from django.utils because we need to get the current time.
from django.utils import timezone
# Import timedelta from datetime because we need to calculate a time difference (12 hours ago).
from datetime import timedelta
# Import Session from rooms.models because this command needs to find and delete old Session objects.
from rooms.models import Session

"""
Author:
This class defines a custom command that can be run from the
server's command line (using 'python manage.py cleanup_sessions').
Its purpose is to automatically clean up the database by finding
and deleting any live study sessions that were created more
than 12 hours ago. This helps keep the session list from
getting cluttered with old, inactive sessions.
"""
class Command(BaseCommand):
    help = 'Deletes sessions older than 12 hours.'

    def handle(self, *args, **kwargs):
        # Calculate the time 12 hours ago from now
        twelve_hours_ago = timezone.now() - timedelta(hours=12)
        
        # Finds all sessions created more than 12 hours ago - maybe
        old_sessions = Session.objects.filter(created_at__lt=twelve_hours_ago)
        
        # Get the count of old sessions found
        count = old_sessions.count()
        
        # If any old sessions were found
        if count > 0:
            # Delete them all
            old_sessions.delete()
            # Print a success message to the command line
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} old session(s).'))
        else:
            # If no old sessions were found, print a message saying so
            self.stdout.write(self.style.SUCCESS('No old sessions to delete.'))
