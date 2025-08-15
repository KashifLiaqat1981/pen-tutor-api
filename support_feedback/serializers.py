# support_feedback/serializers.py
from rest_framework import serializers
from .models import SupportTicket, CourseFeedback, TeacherFeedback, TicketReply
from django.contrib.auth import get_user_model
from authentication.serializers import UserSerializer
User = get_user_model()

# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ['id', 'username', 'email', 'first_name', 'last_name']

class TicketReplySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TicketReply
        fields = ['id', 'message', 'user', 'is_admin_reply', 'created_at']

class SupportTicketSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    replies = TicketReplySerializer(many=True, read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = ['id', 'subject', 'message', 'status', 'priority', 'user', 'created_at', 'updated_at', 'replies']
        read_only_fields = ['user', 'created_at', 'updated_at']

class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['subject', 'message', 'priority']

class CourseFeedbackSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = CourseFeedback
        fields = ['id', 'course_name', 'rating', 'feedback_text', 'user', 'created_at']
        read_only_fields = ['user', 'created_at']

class TeacherFeedbackSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TeacherFeedback
        fields = ['id', 'teacher_name', 'rating', 'feedback_text', 'user', 'created_at']
        read_only_fields = ['user', 'created_at']

class TicketReplyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketReply
        fields = ['message']