# core/utils.py

# Import cache from django.core.cache because 'get_online_user_ids' needs it to read from the cache.
from django.core.cache import cache

# This is the "key" used to store and retrieve the list of online users from the cache.
ONLINE_USERS_CACHE_KEY = 'online_users'

"""
Author:
This is a simple helper function used by many pages (like "Buddies"
and "Sessions"). Its only job is to quickly get the list of
all currently online users from the server's memory (cache).
RT: This function is the central source for all real-time
"who is online" data.
"""
def get_online_user_ids():
    # Now reads the efficient set directly from the cache
    return cache.get(ONLINE_USERS_CACHE_KEY, set())
