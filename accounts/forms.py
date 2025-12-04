# accounts/forms.py

import os
import requests # Added for Resend API
from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from .models import User, ProfileImage
from rooms.models import Course
from django.template.loader import render_to_string

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'age')

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if not email.endswith('@uah.edu'):
            raise forms.ValidationError("You must use a valid @uah.edu email address to sign up.")
        return email

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
    
    # New Age Preference Fields
    match_age_min = forms.IntegerField(
        min_value=18, 
        max_value=99, 
        label="Minimum Match Age",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    match_age_max = forms.IntegerField(
        min_value=18, 
        max_value=99, 
        label="Maximum Match Age",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    interests = forms.ModelMultipleChoiceField(
        queryset=Course.objects.filter(tag_type='interest').order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Interests'
    )

    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.filter(tag_type='course').order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Courses'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'age']

class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form that sends emails via Resend API"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autofocus': True
        }),
        label='Email Address'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control'})

    # Override send_mail to use Resend API
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        
        # Hardcoded subject
        subject = "Password Reset for Charger Circle"
        
        # Render the HTML content from the template
        html_content = render_to_string(email_template_name, context)

        # Get API Key
        resend_api_key = os.environ.get('EMAIL_API_KEY')
        
        if not resend_api_key:
            print("ERROR: EMAIL_API_KEY not set. Cannot send password reset.")
            return

        try:
            response = requests.post(
                "https://api.resend.com/emails",
                json={
                    "from": "Charger Circle <noreply@girlstanding.app>", # Or your verified domain
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content
                },
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error sending password reset email: {e}")

