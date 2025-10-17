# core/utils.py

from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

def get_online_user_ids():
    online_ids = set()
    # This is not efficient for many users, but should be fine for our scale.
    # A better approach for a large site would be to query the cache directly.
    all_users = User.objects.all() 
    for user in all_users:
        last_seen = cache.get(f'last_seen_{user.pk}')
        if last_seen and (timezone.now() - last_seen) < timedelta(minutes=2):
            online_ids.add(user.pk)
    return online_ids
