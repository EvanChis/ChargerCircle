# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ProfileImage, Course

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'age')

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = ProfileImage
        fields = ['image']
        labels = {
            'image': 'Upload a new picture'
        }

class ProfileUpdateForm(forms.ModelForm):
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}), 
        required=False
    )
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.exclude(slug='hang-out'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'age']
