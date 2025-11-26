# rooms/consumers.py

# Import json because WebSocket messages are sent as text in JSON format.
import json
# Import asyncio because 'delayed_disconnect' needs it for 'sleep'.
import asyncio
# Import AsyncWebsocketConsumer from channels.generic.websocket because this is the base class for our real-time consumers.
from channels.generic.websocket import AsyncWebsocketConsumer
# Import database_sync_to_async from channels.db because it lets our async code safely talk to the sync database cache.
from channels.db import database_sync_to_async
# Import cache from django.core.cache because 'update_online_users_cache' needs it.
from django.core.cache import cache

# A global group name for broadcasting presence updates (who is online/offline) to everyone.
PRESENCE_GROUP_NAME = 'global_presence'
# The key used in the cache to store the set of online user IDs.
ONLINE_USERS_CACHE_KEY = 'online_users'

# This dictionary keeps track of scheduled tasks to mark users as offline after a delay.
offline_tasks = {}

"""
Author: Oju
This class handles the main WebSocket connection for each user.
It manages two key real-time features:
1.  **Personal Notifications:** Receiving pop-up messages (like "You matched!")
2.  **Presence:** Tracking who is currently online and broadcasting
    updates (for the green online dots).
RT: This entire class handles real-time notifications and user presence updates.
"""
class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Runs when a user first connects to the site (opens a tab).
    It checks if they are logged in. If so, it adds them to their
    personal notification group and the global presence group.
    It cancels any pending "mark as offline" task if they reconnect
    quickly, marks them as online, and tells everyone else.
    RT: Connects the user to the notification and presence WebSocket channels.
    """
    # Handles per-user notifications and presence - who is online
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            # Unique group name for this user's notifications
            self.group_name = f'notifications_for_user_{self.user.pk}'
            
            # If there's a pending offline task for this user, cancel it
            # This handles cases where the user refreshes or briefly disconnects
            if self.user.pk in offline_tasks:
                offline_tasks[self.user.pk].cancel()
                # Safely remove from dict if it exists to avoid later errors
                try:
                    del offline_tasks[self.user.pk]
                except KeyError:
                    pass

            # Add user to their personal group and the global group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.channel_layer.group_add(PRESENCE_GROUP_NAME, self.channel_name)
            await self.accept() # Accept the WebSocket connection

            # Mark user as online and tell others
            await self.update_user_presence(is_online=True)
        else:
            # If user isn't logged in, close the connection
            await self.close()

    """
    Runs when the user disconnects (closes tab, navigates away).
    Instead of immediately marking them offline, it schedules a task
    to mark them offline after 10 seconds. This prevents them from
    appearing offline if they just refresh the page quickly.
    It immediately removes them from the channel groups though.
    RT: Schedules the user to be marked offline after a delay.
    """
    async def disconnect(self, close_code):
        if hasattr(self, 'user'):
            # Instead of immediately marking as offline, schedule it to happen in 10 seconds
            task = asyncio.create_task(self.delayed_disconnect())
            offline_tasks[self.user.pk] = task
            
            # We still discard the channel from groups immediately
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_discard(PRESENCE_GROUP_NAME, self.channel_name)

    """
    This is the delayed task function. It waits 10 seconds. If the
    task hasn't been cancelled (meaning the user didn't reconnect),
    it proceeds to mark the user as offline and cleans up the task.
    RT: Marks the user as offline if they haven't reconnected within the delay.
    """
    async def delayed_disconnect(self):
        try:
            # Wait for 10 seconds
            await asyncio.sleep(10)
            # If the task hasn't been cancelled, mark the user as offline
            await self.update_user_presence(is_online=False)
            # Clean up the task from our dictionary
            if self.user.pk in offline_tasks:
                del offline_tasks[self.user.pk]
        except asyncio.CancelledError:
            # This catches the error if the task is cancelled while sleeping
            # We do nothing here, essentially keeping the user "online"
            pass

    """
    Receives a notification message sent specifically to this user's
    group and forwards it down the WebSocket to the user's browser.
    RT: Pushes a personal notification (like "You Matched!") to the browser.
    """
    async def send_notification(self, event):
        # receives notifications from channel layer and sends to browser
        await self.send(text_data=json.dumps({'type': 'notification', 'message': event['message']}))
    
    """
    Receives a presence update message (someone went online/offline)
    sent to the global presence group and forwards it down the WebSocket
    to this user's browser.
    RT: Pushes an online/offline status update to the browser for the green dots.
    """
    async def broadcast_presence(self, event):
        # receives presence updates (someone went online/offline) and sends to browser
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'user_pk': event['user_pk'],
            'status': event['status']
        }))

    """
    Updates the central list of online users (stored in the cache)
    and then broadcasts the change (online/offline status) to everyone
    connected to the global presence group.
    RT: Updates the shared online user list and broadcasts the change.
    """
    async def update_user_presence(self, is_online):
        # adds/removes user from a cached set
        await self.update_online_users_cache(is_online)
        # Tell everyone else about the status change
        await self.channel_layer.group_send(
            PRESENCE_GROUP_NAME,
            {'type': 'broadcast_presence', 'user_pk': self.user.pk, 'status': 'online' if is_online else 'offline'}
        )
    
    """
    A helper function that safely adds or removes a user's ID
    from the set of online users stored in the server's cache.
    RT: Async helper to interact with the cache for presence data.
    """
    @database_sync_to_async
    def update_online_users_cache(self, is_online):
        # Get the current set of online IDs from cache, or an empty set
        online_ids = cache.get(ONLINE_USERS_CACHE_KEY, set())
        if is_online:
            online_ids.add(self.user.pk) # Add user if they came online
        else:
            online_ids.discard(self.user.pk) # Remove user if they went offline
        # Save the updated set back to the cache indefinitely
        cache.set(ONLINE_USERS_CACHE_KEY, online_ids, timeout=None) # Persist indefinitely


"""
This class handles the real-time updates within a specific
course room page (the page showing discussion threads). It allows
newly created threads and posts to appear instantly for everyone
viewing that room without needing to refresh the page.
RT: This entire class is for real-time updates in course room discussions.
"""
class RoomConsumer(AsyncWebsocketConsumer):
    """
    Runs when a user opens a specific course room page. It gets the
    room's unique identifier ('slug') from the URL, creates a unique
    group name for that room, and adds the user's connection to that
    group.
    RT: Connects the user to the specific course room's live update channel.
    """
    # Handles live course-room messages
    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'course_room_{self.room_slug}'
        # Add user to the group for this specific course room
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept() # Accept the WebSocket connection

    """
    Runs when the user leaves the course room page or disconnects.
    It removes their connection from the course room's group so they
    no longer receive live updates for that room.
    RT: Disconnects the user from the course room's live update channel.
    """
    async def disconnect(self, close_code):
        # Remove user from the course room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    """
    Receives a message (containing HTML for a new thread or post)
    that was broadcast to this course room's group and forwards it
    down the WebSocket to the user's browser, where JavaScript will
    add it to the page.
    RT: Pushes new thread/post HTML to the user's browser in real-time.
    """
    async def broadcast_message(self, event):
        # when server broadcasts a new thread/post, sends it straight to browser
        await self.send(text_data=json.dumps(event))

