# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.utils import timezone
import json
import logging
from .models import ChatRoom, Message, MessageRead
from django.contrib.auth import get_user_model
from .services.content_filter import filter_message

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        # Ensure room_id is string
        self.room_id_str = str(self.room_id)
        self.room_group_name = f"chat_{self.room_id_str}"

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        try:
            # Check if user is participant
            is_allowed = await self.is_user_allowed(self.user.id, self.room_id_str)
            if not is_allowed:
                await self.close(code=4003)
                return

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
            logger.info(f"User {self.user.id} connected to room {self.room_id_str}")
        except Exception as e:
            logger.error(f"Error in connect: {e}")
            await self.close(code=4004)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def is_user_allowed(self, user_id, room_id_str):
        try:
            room = ChatRoom.objects.get(id=room_id_str, is_active=True)
            return room.participants.filter(id=user_id).exists()
        except (ChatRoom.DoesNotExist, ValueError):
            return False

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            event_type = data.get("type")

            if event_type == "message.send":
                await self.handle_send_message(data)
            elif event_type == "message.read":
                await self.handle_read_message(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error in receive: {e}")

    async def handle_send_message(self, data):
        content = data.get("content")
        if not content:
            return

        try:
            # Filter content
            filtered_content, has_forbidden, blocked_type = await sync_to_async(filter_message)(content)

            # Save message
            msg_data = await self.save_message(
                user_id=self.user.id,
                room_id=self.room_id_str,
                original_content=content,
                filtered_content=filtered_content,
                has_forbidden=has_forbidden,
                blocked_type=blocked_type
            )

            await self.mark_as_delivered(msg_data['id'])

            # Create simple serialized data with all strings
            serialized = {
                'id': str(msg_data['id']),  # Ensure ID is string
                'room': self.room_id_str,  # Use string room ID
                'sender': {
                    'id': str(self.user.id),
                    'username': msg_data['sender_username'],
                    'role': self.user.role,
                    'teacher_id': str(getattr(self.user.teacher_profile, 'teacher_id', None)),
                    'student_id': str(getattr(self.user.student_profile, 'student_id', None)),
                },
                'message_type': msg_data['message_type'],
                'content': msg_data['content'],
                'original_content': msg_data['original_content'],
                'status': msg_data['status'],
                'has_forbidden_content': msg_data['has_forbidden_content'],
                'blocked_content_type': msg_data['blocked_content_type'],
                'read_by_users': [],
                'is_read_by_me': False
            }

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": serialized
                }
            )
        except Exception as e:
            logger.error(f"Error in handle_send_message: {e}")

    async def handle_read_message(self, data):
        message_id = data.get("message_id")
        if not message_id:
            return

        try:
            await self.mark_as_read(message_id, self.user.id)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.read",
                    "message_id": str(message_id),
                    "user_id": str(self.user_id) # Ensure string
                }
            )
        except Exception as e:
            logger.error(f"Error in handle_read_message: {e}")

    async def chat_message(self, event):
        try:
            await self.send(text_data=json.dumps({
                "type": "message.new",
                "message": event["message"]
            }))
        except Exception as e:
            logger.error(f"Error in chat_message: {e}")

    async def chat_read(self, event):
        try:
            await self.send(text_data=json.dumps({
                "type": "message.read",
                "message_id": event["message_id"],
                "user_id": event["user_id"]
            }))
        except Exception as e:
            logger.error(f"Error in chat_read: {e}")

    @database_sync_to_async
    def save_message(self, user_id, room_id, original_content, filtered_content, has_forbidden, blocked_type):
        from django.db import transaction

        with transaction.atomic():
            user = User.objects.get(id=user_id)
            room = ChatRoom.objects.get(id=self.room_id)

            # Determine role without triggering related queries
            role = getattr(user, "role", "unknown")

            msg = Message.objects.create(
                room=room,
                sender=user,
                content=filtered_content,
                original_content=original_content if has_forbidden else "",
                has_forbidden_content=has_forbidden,
                blocked_content_type=blocked_type,
                status="blocked" if has_forbidden else "sent"
            )

            room.updated_at = timezone.now()
            room.save(update_fields=["updated_at"])

            # Return as dict with all values as strings or simple types
            return {
                'id': msg.id,
                'sender_id': str(user.id),
                'sender_username': user.username,
                'sender_role': role,
                'message_type': msg.message_type,
                'content': msg.content,
                'original_content': msg.original_content,
                'status': msg.status,
                'has_forbidden_content': msg.has_forbidden_content,
                'blocked_content_type': msg.blocked_content_type,
                'created_at': msg.created_at,
            }

    @database_sync_to_async
    def mark_as_delivered(self, message_id):
        Message.objects.filter(id=message_id).update(status="delivered")

    @database_sync_to_async
    def mark_as_read(self, message_id, user_id):
        try:
            message = Message.objects.select_related("room").get(id=message_id)
            if str(message.room.id) != self.room_id_str:
                return
            if not message.room.participants.filter(id=user_id).exists():
                return
            MessageRead.objects.get_or_create(message=message, user_id=user_id)
        except Message.DoesNotExist:
            return