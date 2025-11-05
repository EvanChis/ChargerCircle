# accounts/models.py

# Import models from django.db because this file defines database models.
from django.db import models
# Import AbstractUser from django.contrib.auth.models because 'User' is based on it.
from django.contrib.auth.models import AbstractUser
# Import CustomUserManager from .managers because the 'User' model needs it.
from .managers import CustomUserManager
# Import Course from rooms.models because 'User' needs a relation to it.
from rooms.models import Course

"""
Author: Evan
This class defines the main "User" account for the entire
application. It's customized to use an email address instead
of a username for logging in. It also stores the user's
personal info (name, age), what courses they are in, and
a list of their "buddies" (other users they have matched with).
"""
class User(AbstractUser):
    # Custom setup to use email instead of username
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    
    # Custom fields
    age = models.PositiveIntegerField(blank=True, null=True)
    courses = models.ManyToManyField(Course, related_name='students', blank=True)
    buddies = models.ManyToManyField('self', symmetrical=False, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

"""
Author: Evan
This class holds extra information that is attached to a
User account. It's connected one-to-one with a User and
stores their personal "bio". It also has a helper function
to easily find the URL of the user's main profile picture.
"""
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    
    @property
    def main_image_url(self):
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url
        return None

    def __str__(self):
        return f'{self.user.email} Profile'

"""
Author: Evan
This class represents a single picture that a user has
uploaded to their profile. It links the image file to the
user's profile and includes a flag ('is_main') to mark
which picture should be their main display photo.
"""
class ProfileImage(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='profile_images/')
    is_main = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.profile.user.email}"

"""
Author: Evan
This class represents a "Like" from the Discover page. It
records who gave the like ('from_user') and who received it
('to_user'). These records are checked to see if a
mutual match has occurred.
RT: This table is created and checked by the real-time HTMX
views on the Discover page.
"""
# This new model will track "likes" from the Discover page.
class Like(models.Model):
    from_user = models.ForeignKey(User, related_name='likes_given', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='likes_received', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.first_name} likes {self.to_user.first_name}"

"""
Author: Evan
This class tracks every action a user takes on the Discover
page (both "Likes" and "Skips"). This does two things:
1. It prevents a user from seeing the same person again
   in Discover.
2. It creates a "history" that allows a user to undo their
   last action.
RT: This table is written to by the HTMX "like" and "skip"
views and read by the HTMX "undo" view.
"""
class SkippedMatch(models.Model):
    ACTION_CHOICES = (
        ('skip', 'Skip'),
        ('like', 'Like'),
    )
    from_user = models.ForeignKey(User, related_name='actions', on_delete=models.CASCADE)
    skipped_user = models.ForeignKey(User, related_name='was_actioned_by', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    action_type = models.CharField(max_length=4, choices=ACTION_CHOICES, default='skip')


    class Meta:
        # Ensures we don't have duplicate skip entries
        unique_together = ('from_user', 'skipped_user')
        ordering = ['-timestamp'] # Part of Undo

    def __str__(self):
        return f"{self.from_user.first_name} {self.action_type}d {self.skipped_user.first_name}"

