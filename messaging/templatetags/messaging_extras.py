# messaging/templatetags/messaging_extras.py

# Import template from django because this file defines a custom template filter.
from django import template

"""
Author:
This line creates a "registry" that allows us to make our
own custom functions (called "filters") available to use
directly in the HTML templates.
"""
register = template.Library()

"""
Author:
This function defines a custom "filter" that can be used
in HTML. It's used to split a piece of text into a list
based on a separator. For example, it's used on the
"invite_message.html" template to break up the special
invite message into usable parts.
RT: This supports the HTMX-powered session invite card
by parsing the message content.
"""
@register.filter
def split(value, key):
    
    # Splits a string by the given key.
    
    return value.split(key)
