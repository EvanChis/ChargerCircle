# core/utils.py

from django.core.cache import cache

ONLINE_USERS_CACHE_KEY = 'online_users'

def get_online_user_ids():
    # Now reads the efficient set directly from the cache
    return cache.get(ONLINE_USERS_CACHE_KEY, set())
