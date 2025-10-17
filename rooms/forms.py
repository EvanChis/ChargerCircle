# rooms/forms.py

from django import forms
from .models import Thread, Post, Session

class ThreadForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}), 
        label="Your Post"
    )
    
    class Meta:
        model = Thread
        fields = ['title', 'content']

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content']

# Custom field to display user's full name
class BuddyChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.first_name} {obj.last_name}"

class SessionCreateForm(forms.ModelForm):

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
