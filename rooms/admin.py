# rooms/admin.py

# Import admin from django.contrib because this file configures the admin site.
from django.contrib import admin
# Import models from .models because Course, Thread, Post, Session need to be registered.
from .models import Course, Thread, Post, Session

"""
Author: Angie
This class customizes how the 'Session' model appears in the
Django admin site. It specifically lists the topic, course,
host, and creation time in the main list view. It also attempts
to make all fields editable, although Django might override this
for automatically set fields like 'created_at'.
"""
class SessionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'course', 'host', 'created_at') # columns shown when you open the Session list in admin
    
    # This method overrides Django's default behavior and makes all fields,
    # including the auto-timestamp, editable in the detail view. or it's supposed to maybe at least
    def get_readonly_fields(self, request, obj=None):
        return []

class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tag_type') # Add 'tag_type'
    list_filter = ('tag_type',) # Add a filter
    search_fields = ('name', 'slug')

"""
Author: Angie
This block of code makes the main database tables for the
'rooms' app (Course, Thread, Post, Session) visible and
editable within the Django admin control panel.
"""
admin.site.register(Course, CourseAdmin)
admin.site.register(Thread)
admin.site.register(Post)
admin.site.register(Session, SessionAdmin)
