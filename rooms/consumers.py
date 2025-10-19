# rooms/consumers.py

import json # turns Python objects into text and back
from channels.generic.websocket import AsyncWebsocketConsumer # a class that helps talk to browser in real-time (websockets)
from channels.db import database_sync_to_async # helper to call normal DB code from async code
from django.core.cache import cache
from django.utils import timezone
from asgiref.sync import async_to_sync # # calls async code from sync code

PRESENCE_GROUP_NAME = 'global_presence'

# Handles per-user notifications and presence - who is online
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            self.group_name = f'notifications_for_user_{self.user.pk}'
            
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.channel_layer.group_add(PRESENCE_GROUP_NAME, self.channel_name)
            await self.accept()

            # marks user as online and tells others
            await self.update_user_presence(is_online=True)
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'user'):
            # mark user offline
            await self.update_user_presence(is_online=False)
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_discard(PRESENCE_GROUP_NAME, self.channel_name)

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
        # helper: stores last-seen and broadcasts online/offline
        await self.set_cache_last_seen() # sets a timestamp in cache
        await self.channel_layer.group_send(
            PRESENCE_GROUP_NAME,
            {'type': 'broadcast_presence', 'user_pk': self.user.pk, 'status': 'online' if is_online else 'offline'}
        )
    
    @database_sync_to_async
    def set_cache_last_seen(self):
        # stores 'last seen' time for this user for 5 minutes
        cache.set(f'last_seen_{self.user.pk}', timezone.now(), 300)



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
