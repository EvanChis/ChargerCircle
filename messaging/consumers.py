# messaging/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from .models import Message, MessageThread

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.thread_id = self.scope['url_route']['kwargs']['thread_id']
        self.room_group_name = f'chat_{self.thread_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'chat_message')

        if message_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'typing_indicator', 'sender_id': data['sender_id']}
            )
        else:
            message_content = data['message']
            sender_id = data['sender_id']
            sender_first_name = data['sender_first_name']
            try:
                sender = await self.get_user_instance(sender_id)
                thread = await self.get_thread_instance(self.thread_id)
                
                await self.create_message(thread, sender, message_content)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message', 
                        'message': message_content, 
                        'sender_id': sender_id,
                        'sender_first_name': sender_first_name
                    }
                )
            except Exception as e:
                print(f"ERROR in ChatConsumer: {e}")

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message', 
            'message': event['message'], 
            'sender_id': event['sender_id'],
            'sender_first_name': event['sender_first_name']
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing', 
            'sender_id': event['sender_id']
        }))
    
    @sync_to_async
    def create_message(self, thread, sender, content):
        new_message = Message.objects.create(thread=thread, sender=sender, content=content)
        thread.save() # Updates message thread's timestamp
        return new_message

    @sync_to_async
    def get_user_instance(self, user_id):
        return User.objects.get(pk=user_id)
        
    @sync_to_async
    def get_thread_instance(self, thread_id):
        return MessageThread.objects.get(pk=thread_id)
    