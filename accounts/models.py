# accounts/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager
from rooms.models import Course
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    
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
    
    match_age_min = models.PositiveIntegerField(default=18)
    match_age_max = models.PositiveIntegerField(default=99)
    
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

    def save(self, *args, **kwargs):
        if self.image:
            if hasattr(self.image, 'seek'):
                self.image.seek(0)

            try:
                img = Image.open(self.image)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                max_size = (800, 800)
                
                if img.height > max_size[1] or img.width > max_size[0]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    output = BytesIO()
                    img.save(output, format='JPEG', quality=75)
                    output.seek(0)
                    
                    new_name = os.path.splitext(self.image.name)[0] + '.jpg'
                    self.image = ContentFile(output.read(), name=new_name)
                else:
                    if hasattr(self.image, 'seek'):
                        self.image.seek(0)

            except Exception as e:
                print(f"Error optimizing image: {e}")
                if hasattr(self.image, 'seek'):
                    self.image.seek(0)

        super().save(*args, **kwargs)

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
        unique_together = ('from_user', 'skipped_user')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.from_user.first_name} {self.action_type}d {self.skipped_user.first_name}"

