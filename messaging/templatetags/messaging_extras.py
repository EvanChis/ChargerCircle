# messaging/templatetags/messaging_extras.py

from django import template

register = template.Library()

@register.filter
def split(value, key):
    """
    Splits a string by the given key.
    """
    return value.split(key)
