# rooms/forms.py

from django import forms # helper to make HTML forms and validate input
from .models import Thread, Post, Session # our database tables

class ThreadForm(forms.ModelForm):
    # form to make a new discussion thread
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}), 
        label="Your Post"
    )
    
    class Meta:
        model = Thread
        fields = ['title', 'content']

class PostForm(forms.ModelForm):
    # form to reply
    class Meta:
        model = Post
        fields = ['content']

# Shows buddies by First Last
class BuddyChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.first_name} {obj.last_name}"

class SessionCreateForm(forms.ModelForm):
    # form to create a live session and optionally invite buddies
    buddies_to_invite = BuddyChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Invite Buddies"
    )

    class Meta:
        model = Session
        fields = ['course', 'topic', 'buddies_to_invite']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Excludes the current user from the list of buddies
            self.fields['buddies_to_invite'].queryset = user.buddies.exclude(pk=user.pk)
