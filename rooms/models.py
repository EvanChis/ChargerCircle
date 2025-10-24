# rooms/models.py

from django.db import models
from django.conf import settings

# Course/Rooms/Activities/Events Model
class Course(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

# A Thread is a discussion inside a Room (a forum thread)
class Thread(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='threads')
    title = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
# A Post is a single message inside a Thread
class Post(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Post by {self.author} in {self.thread.title}'

# A Session is a live study/hangout for a Course
class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_sessions')
    topic = models.CharField(max_length=255)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='joined_sessions', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"'{self.topic}' for {self.course.name}"
