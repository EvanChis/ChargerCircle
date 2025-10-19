# rooms/admin.py

from django.contrib import admin
from .models import Course, Thread, Post, Session

class SessionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'course', 'host', 'created_at') # columns shown when you open the Session list in admin
    
    # This method overrides Django's default behavior and makes all fields,
    # including the auto-timestamp, editable in the detail view. or it's supposed to maybe at least
    def get_readonly_fields(self, request, obj=None):
        return []

admin.site.register(Course)
admin.site.register(Thread)
admin.site.register(Post)
admin.site.register(Session, SessionAdmin)
