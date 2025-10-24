# accounts/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager
from rooms.models import Course

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

class ProfileImage(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='profile_images/')
    is_main = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.profile.user.email}"

# This new model will track "likes" from the Discover page.
class Like(models.Model):
    from_user = models.ForeignKey(User, related_name='likes_given', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='likes_received', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.first_name} likes {self.to_user.first_name}"

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
