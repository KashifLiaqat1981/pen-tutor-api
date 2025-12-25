# models.py
from django.db import models
# from django.conf import settings
from authentication.models import User
import re
from django.core.exceptions import ValidationError

# User= settings.AUTH_USER_MODEL

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('course', 'Course Discussion'),
        ('meeting', 'Meeting Chat'),
        ('job', 'Job Discussion'),
        ('general', 'General Chat')
    ]

    name = models.CharField(max_length=255)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    description = models.TextField(blank=True)

    participants = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Reference fields for linking to specific entities
    course_id = models.IntegerField(null=True, blank=True)  # Link to course
    meeting_id = models.IntegerField(null=True, blank=True)  # Link to meeting
    job_id = models.IntegerField(null=True, blank=True)  # Link to job
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms',null=True,blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"


class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('file', 'File Attachment'),
        ('image', 'Image'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('blocked', 'Blocked'),  # For messages with forbidden content
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    original_content = models.TextField(blank=True)  # Store original before filtering

    # Message status and moderation
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    has_forbidden_content = models.BooleanField(default=False)
    blocked_content_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Comma-separated list of blocked content types: email, phone, social_link"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} in {self.room.name}: {self.content[:50]}..."


class MessageRead(models.Model):
    """Track message read status for each user"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user']

    def __str__(self):
        return f"{self.user.username} read {self.message.id}"
