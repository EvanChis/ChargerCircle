# rooms/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from asgiref.sync import async_to_sync

PRESENCE_GROUP_NAME = 'global_presence'

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            self.group_name = f'notifications_for_user_{self.user.pk}'
            
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.channel_layer.group_add(PRESENCE_GROUP_NAME, self.channel_name)
            await self.accept()

            # Calls the async version directly
            await self.update_user_presence(is_online=True)
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'user'):
            await self.update_user_presence(is_online=False)
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_discard(PRESENCE_GROUP_NAME, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({'type': 'notification', 'message': event['message']}))
    
    async def broadcast_presence(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'user_pk': event['user_pk'],
            'status': event['status']
        }))

    
    async def update_user_presence(self, is_online):
        await self.set_cache_last_seen()
        await self.channel_layer.group_send(
            PRESENCE_GROUP_NAME,
            {'type': 'broadcast_presence', 'user_pk': self.user.pk, 'status': 'online' if is_online else 'offline'}
        )
    
    # Database/cache operations need to be wrapped for async context
    @database_sync_to_async
    def set_cache_last_seen(self):
        cache.set(f'last_seen_{self.user.pk}', timezone.now(), 300)



class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'course_room_{self.room_slug}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps(event))
