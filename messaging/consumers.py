# messaging/consumers.py

# Import json because WebSocket messages are sent as text in JSON format.
import json
# Import AsyncWebsocketConsumer from channels.generic.websocket because this is the base class for our real-time consumer.
from channels.generic.websocket import AsyncWebsocketConsumer
# Import get_user_model from django.contrib.auth because we need to get the User who sent a message.
from django.contrib.auth import get_user_model
# Import sync_to_async from asgiref.sync because it lets our async code safely talk to the sync database.
from asgiref.sync import sync_to_async
# Import models from .models because we need to create 'Message' and find 'MessageThread'.
from .models import Message, MessageThread

User = get_user_model()

"""
Author: Oju
This class is the "brain" for the real-time private chat. It
handles the WebSocket connection for a single chat thread. It
manages users connecting, disconnecting, sending messages, and
receiving messages, all live without a page refresh.
RT: This entire class is for real-time chat functionality.
"""
class ChatConsumer(AsyncWebsocketConsumer):
    """
    This function runs the moment a user opens a chat window.
    It gets the thread ID from the URL, creates a unique
    "group name" for that chat room, and adds the user's
    connection to that group.
    RT: This connects the user to the live chat channel.
    """
    async def connect(self):
        self.thread_id = self.scope['url_route']['kwargs']['thread_id']
        self.room_group_name = f'chat_{self.thread_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    """
    This function runs when the user closes the chat window
    or disconnects. It removes the user's connection from the
    chat room's "group," so they no longer receive messages.
    RT: This disconnects the user from the live chat channel.
    """
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    """
    This function runs every time the server receives a
    message *from* the user's browser (e.g., they hit "Send"
    or start typing). It checks if the message is a "typing"
    notification or an actual "chat_message".
    RT: This receives live messages and "typing" notifications
    from the user's browser.
    """
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'chat_message')

        # --- WebRTC Hangup handler ---
        if message_type == 'typing':
            # If it's a "typing" message, just broadcast it to the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'sender_id': data['sender_id'],
                    'sender_first_name': data.get('sender_first_name', 'Someone') # <-- CHANGE HERE
                }
            )
        
        elif message_type == 'webrtc_offer':
            # A user is sending an offer. Broadcast it.
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_receive_offer',
                    'sender_id': data['sender_id'],
                    'sender_first_name': data['sender_first_name'],
                    'offer_sdp': data['offer_sdp']
                }
            )
            
        elif message_type == 'webrtc_answer':
            # A user is sending an answer. Broadcast it.
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_receive_answer',
                    'sender_id': data['sender_id'],
                    'answer_sdp': data['answer_sdp']
                }
            )
            
        elif message_type == 'webrtc_ice_candidate':
            # A user is sending a new ice candidate. Broadcast it.
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_receive_ice_candidate',
                    'sender_id': data['sender_id'],
                    'candidate': data['candidate'] # Pass the candidate
                }
            )
            
        elif message_type == 'webrtc_hangup':
            # A user is hanging up. Broadcast it.
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_receive_hangup',
                    'sender_id': data['sender_id']
                }
            )

        elif message_type == 'chat_message':
            message_content = data['message']
            sender_id = data['sender_id']
            sender_first_name = data['sender_first_name']
            try:
                sender = await self.get_user_instance(sender_id)
                thread = await self.get_thread_instance(self.thread_id)
                
                # Only save content if it's not None
                if message_content:
                    await self.create_message(thread, sender, message_content)
                

                # After saving, broadcast the new message to the group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message', 
                        'message': message_content, 
                        'image_url': None,
                        'sender_id': sender_id,
                        'sender_first_name': sender_first_name
                    }
                )
            except Exception as e:
                print(f"ERROR in ChatConsumer: {e}")

    """
    This function is called when the server's broadcast
    system (the "group") gets a 'chat_message' to send out.
    It takes that message and pushes it down the WebSocket
    to the user's browser so it appears on their screen.
    RT: This pushes a new chat message to the user's screen.
    """
    async def chat_message(self, event):
        # Author: Angie
        # Includes 'image_url' if it exists.
        await self.send(text_data=json.dumps({
            'type': 'chat_message', 
            'message': event.get('message'), 
            'image_url': event.get('image_url'),
            'sender_id': event['sender_id'],
            'sender_first_name': event['sender_first_name']
        }))


    """
    This function is called when the broadcast system gets a
    'typing_indicator' to send. It pushes the "is typing"
    notification down the WebSocket to the user's browser.
    RT: This pushes the "is typing" notification to the user's screen.
    """
    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing', 
            'sender_id': event['sender_id'],
            'sender_first_name': event.get('sender_first_name') # <-- CHANGE HERE
        }))
    
    
    # --- WebRTC HANDLERS ---
    
    # Broadcasts the offer to the other user
    async def webrtc_receive_offer(self, event):
        await self.send(text_data=json.dumps({
            'type': 'webrtc_offer', 
            'sender_id': event['sender_id'],
            'sender_first_name': event['sender_first_name'],
            'offer_sdp': event['offer_sdp']
        }))

    # Broadcasts the answer back to the original caller
    async def webrtc_receive_answer(self, event):
        await self.send(text_data=json.dumps({
            'type': 'webrtc_answer',
            'sender_id': event['sender_id'],
            'answer_sdp': event['answer_sdp']
        }))
        
    # Broadcasts the ICE candidate to the other user
    async def webrtc_receive_ice_candidate(self, event):
        await self.send(text_data=json.dumps({
            'type': 'webrtc_ice_candidate',
            'sender_id': event['sender_id'],
            'candidate': event['candidate']
        }))
        
    # Broadcasts the hangup signal to the other user
    async def webrtc_receive_hangup(self, event):
        await self.send(text_data=json.dumps({
            'type': 'webrtc_hangup',
            'sender_id': event['sender_id']
        }))
        
    # --- END WebRTC HANDLERS ---
    
    
    """
    This is a helper function that safely saves a new
    message to the database from within the async code.
    RT: This is an async helper for the real-time 'receive' function.
    """
    @sync_to_async
    def create_message(self, thread, sender, content):
        new_message = Message.objects.create(thread=thread, sender=sender, content=content)
        thread.save() # Updates message thread's timestamp
        return new_message

    """
    This is a helper function that safely gets a User object
    from the database from within the async code.
    RT: This is an async helper for the real-time 'receive' function.
    """
    @sync_to_async
    def get_user_instance(self, user_id):
        return User.objects.get(pk=user_id)
        
    """
    This is a helper function that safely gets a MessageThread
    object from the database from within the async code.
    RT: This is an async helper for the real-time 'receive' function.
    """
    @sync_to_async
    def get_thread_instance(self, thread_id):
        return MessageThread.objects.get(pk=thread_id)

