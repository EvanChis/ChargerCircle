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
    buddies = models.ManyToManyField('self', symmetrical=False, blank=True) # This line is critical

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

class BuddyRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='from_user', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='to_user', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.from_user.email} to {self.to_user.email}"

class SkippedMatch(models.Model):
    from_user = models.ForeignKey(User, related_name='skipper', on_delete=models.CASCADE)
    skipped_user = models.ForeignKey(User, related_name='was_skipped_by', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensures we don't have duplicate skip entries
        unique_together = ('from_user', 'skipped_user')

    def __str__(self):
        return f"{self.from_user.first_name} skipped {self.skipped_user.first_name}"
