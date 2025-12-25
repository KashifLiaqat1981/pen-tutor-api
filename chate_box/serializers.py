# serializers.py - Simplified version
from rest_framework import serializers
from job_board.models import JobApplication
from authentication.models import User
from .models import ChatRoom, Message, MessageRead


class ChatUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'role']

    def get_role(self, obj):
        # Safe method that doesn't trigger DB queries
        if hasattr(obj, '_teacher_profile_id') or hasattr(obj, 'teacher_profile_id'):
            return 'teacher'
        if hasattr(obj, '_student_profile_id') or hasattr(obj, 'student_profile_id'):
            return 'student'
        return 'user'

    def get_full_name(self, obj):
        name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return name or obj.username


class MessageSerializer(serializers.ModelSerializer):
    sender = ChatUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'message_type', 'content', 'original_content',
            'file_url', 'file_name', 'status', 'is_edited', 'edited_at',
            'has_forbidden_content', 'blocked_content_type', 'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'sender', 'original_content', 'status', 'has_forbidden_content',
            'blocked_content_type', 'created_at', 'updated_at'
        ]


class ChatRoomSerializer(serializers.ModelSerializer):
    participants = ChatUserSerializer(many=True, read_only=True)
    participants_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'room_type', 'description', 'created_by',
            'participants', 'participants_ids', 'is_active', 'created_at',
            'updated_at', 'course_id', 'meeting_id', 'job_id'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class JobApplicationChatSerializer(serializers.ModelSerializer):
    job_post = serializers.PrimaryKeyRelatedField(read_only=True)
    chat_room = ChatRoomSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            'id', 'job_post', 'status', 'applied_at', 'chat_room',
            'finalized_days', 'finalized_time_start', 'finalized_time_end',
            'finalized_budget', 'demo_class_time', 'is_finalized', 'teacher_finalized',
            'student_finalized', 'both_finalized', 'finalized_at'
        ]