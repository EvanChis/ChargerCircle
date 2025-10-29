# rooms/consumers.py

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache

PRESENCE_GROUP_NAME = 'global_presence'
ONLINE_USERS_CACHE_KEY = 'online_users'

# This dictionary will hold our disconnect tasks
offline_tasks = {}

class NotificationConsumer(AsyncWebsocketConsumer):
    # Handles per-user notifications and presence - who is online
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            self.group_name = f'notifications_for_user_{self.user.pk}'
            
            # If there's a pending offline task for this user, cancel it
            if self.user.pk in offline_tasks:
                offline_tasks[self.user.pk].cancel()
                del offline_tasks[self.user.pk]

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.channel_layer.group_add(PRESENCE_GROUP_NAME, self.channel_name)
            await self.accept()

            # Mark user as online and tell others
            await self.update_user_presence(is_online=True)
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'user'):
            # Instead of immediately marking as offline, schedule it to happen in 10 seconds
            task = asyncio.create_task(self.delayed_disconnect())
            offline_tasks[self.user.pk] = task
            
            # We still discard the channel from groups immediately
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_discard(PRESENCE_GROUP_NAME, self.channel_name)

    async def delayed_disconnect(self):
        # Wait for 10 seconds
        await asyncio.sleep(10)
        # If the task hasn't been cancelled, mark the user as offline
        await self.update_user_presence(is_online=False)
        # Clean up the task from our dictionary
        if self.user.pk in offline_tasks:
            del offline_tasks[self.user.pk]

    async def send_notification(self, event):
        # receives notifications from channel layer and sends to browser
        await self.send(text_data=json.dumps({'type': 'notification', 'message': event['message']}))
    
    async def broadcast_presence(self, event):
        # receives presence updates (someone went online/offline) and sends to browser
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'user_pk': event['user_pk'],
            'status': event['status']
        }))

    async def update_user_presence(self, is_online):
        # adds/removes user from a cached set
        await self.update_online_users_cache(is_online)
        await self.channel_layer.group_send(
            PRESENCE_GROUP_NAME,
            {'type': 'broadcast_presence', 'user_pk': self.user.pk, 'status': 'online' if is_online else 'offline'}
        )
    
    @database_sync_to_async
    def update_online_users_cache(self, is_online):
        online_ids = cache.get(ONLINE_USERS_CACHE_KEY, set())
        if is_online:
            online_ids.add(self.user.pk)
        else:
            online_ids.discard(self.user.pk)
        cache.set(ONLINE_USERS_CACHE_KEY, online_ids, timeout=None) # Persist indefinitely


class RoomConsumer(AsyncWebsocketConsumer):
    # Handles live course-room messages
    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'course_room_{self.room_slug}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def broadcast_message(self, event):
        # when server broadcasts a new thread/post, sends it straight to browser
        await self.send(text_data=json.dumps(event))
