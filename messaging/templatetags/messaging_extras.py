import re
from django import template
from django.utils.html import escape, mark_safe

register = template.Library()

# Regex to find URLs
URL_REGEX = re.compile(
    r'(https?://\S+|www\.\S+)'
)

@register.filter
def split(value, key):
    return value.split(key)

@register.filter
def linkify(text):
    if not text:
        return ""
    safe_text = escape(text)
    def replace(match):
        url = match.group(0)
        href = url
        if not href.startswith('http'):
            href = 'http://' + href
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer" style="text-decoration: underline; color: inherit;">{url}</a>'
    linked_text = URL_REGEX.sub(replace, safe_text)
    return mark_safe(linked_text)
