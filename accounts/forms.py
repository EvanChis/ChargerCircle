# accounts/forms.py

# Import forms from django because this file defines web forms.
from django import forms
# Import UserCreationForm from django.contrib.auth.forms because 'CustomUserCreationForm' is based on it.
from django.contrib.auth.forms import UserCreationForm
# Import models from .models because 'User', 'ProfileImage', and 'Course' are needed for the forms.
from .models import User, ProfileImage, Course

"""
Author:
This class defines the form fields shown on the "Sign Up" page.
It's based on Django's standard user creation form but is
customized to use the email address as the username and to
ask for first name, last name, and age.
"""
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'age')

"""
Author:
This class defines the form used for uploading a new profile
picture on the "Edit Profile" page. It is a simple form that
only contains a single file upload field for an image.
"""
class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = ProfileImage
        fields = ['image']
        labels = {
            'image': 'Upload a new picture'
        }

"""
Author:
This class defines the main form on the "Edit Profile" page.
It allows a user to update their basic details (name, age),
write a personal bio, and select which courses they are in
from a list of checkboxes.
"""
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
