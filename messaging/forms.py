# messaging/forms.py

from django import forms
from .models import Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={'placeholder': 'Write a message...', 'class': 'message-input', 'autofocus': True})
        }
        labels = {
            'content': ''
        }
