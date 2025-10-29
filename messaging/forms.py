# messaging/forms.py

# Import forms from django because this file defines a web form.
from django import forms
# Import Message from .models because the 'MessageForm' is based on the 'Message' database model.
from .models import Message

"""
Author:
This class defines the form used for typing and sending a
new message in the chat window. It's based directly on the
'Message' database model, specifically using only the 'content'
field. It also adds some styling and usability features like
placeholder text and automatically focusing the input field.
RT: This form is used to send messages via the real-time
WebSocket chat.
"""
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={'placeholder': 'Write a message...', 'class': 'message-input', 'autofocus': True})
        }
        labels = {
            'content': '' # Hides the label for the message input field
        }
