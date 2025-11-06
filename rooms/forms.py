# rooms/forms.py

# Import forms from django because this file defines web forms.
from django import forms # helper to make HTML forms and validate input
# Import Thread, Post, Session from .models because the forms are based on these database tables.
from .models import Thread, Post, Session # our database tables

"""
Author: Angie
This class defines the form used for creating a new discussion
thread within a course room. It includes fields for the
thread's title and the content of the first post.
"""
class ThreadForm(forms.ModelForm):
    # form to make a new discussion thread
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Your Post"
    )
    
    class Meta:
        model = Thread
        fields = ['title', 'content']

"""
Author: Angie
This class defines the form used for writing a reply (a post)
within an existing discussion thread. It only contains a single
field for the message content.
"""
class PostForm(forms.ModelForm):
    # form to reply
    class Meta:
        model = Post
        fields = ['content']

"""
Author: Angie
This is a helper class to customize how connections are displayed
in the 'SessionCreateForm'. Instead of showing just their
email or ID, it makes the form display their full first and
last name, which is more user-friendly.
"""
# Shows connections by First Last
class BuddyChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.first_name} {obj.last_name}"

"""
Author: Angie
This class defines the form used for creating a new live study
session. It includes fields to select the course, enter a topic,
and optionally choose connections to invite using checkboxes. The
list of connections to invite is customized to show full names and
excludes the user creating the session.
"""
class SessionCreateForm(forms.ModelForm):
    # form to create a live session and optionally invite connections
    buddies_to_invite = BuddyChoiceField(
        queryset=None, # The actual list of connections is set below
        widget=forms.CheckboxSelectMultiple, # Display as checkboxes
        required=False, # Inviting connections is optional
        label="Invite Connections"
    )

    class Meta:
        model = Session
        fields = ['course', 'topic', 'buddies_to_invite']

    # This special method runs when the form is created
    def __init__(self, *args, **kwargs):
        # Get the user who is creating the session (passed in from the view)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Set the list of choices for 'buddies_to_invite' to be the user's buddies,
            # excluding themselves from the list.
            self.fields['buddies_to_invite'].queryset = user.buddies.exclude(pk=user.pk)

