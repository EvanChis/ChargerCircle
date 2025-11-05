# rooms/models.py

# Import models from django.db because this file defines database models.
from django.db import models
# Import settings from django.conf because 'Thread', 'Post', and 'Session' need to link to the User model.
from django.conf import settings

"""
Author: Angie
This class represents a course or topic that users can be
associated with. It's used both for matching users in Discover
and for organizing discussion rooms and study sessions. The
'slug' is a URL-friendly version of the name.
"""
# Course/Rooms/Activities/Events Model
class Course(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True) # URL-friendly identifier
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

"""
Author: Angie
This class represents a single discussion thread within a
specific 'Course' room. It stores the title of the discussion
and links to the 'author' (the user who started it) and the
'course' it belongs to.
"""
# A Thread is a discussion inside a Room (a forum thread)
class Thread(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='threads')
    title = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

"""
Author: Angie
This class represents a single message or reply within a
discussion 'Thread'. It stores the actual text content, links
to the 'author' who wrote it, and the 'thread' it's a part of.
"""
# A Post is a single message inside a Thread
class Post(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Post by {self.author} in {self.thread.title}'

"""
Author: Angie
This class represents a live study or hangout session associated
with a specific 'Course'. It stores the session 'topic', who
created it ('host'), and keeps a list of all the users who
have joined ('participants').
"""
# A Session is a live study/hangout for a Course
class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_sessions')
    topic = models.CharField(max_length=255)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='joined_sessions', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"'{self.topic}' for {self.course.name}"
    
