# activity/serializers.py
from rest_framework import serializers
from .models import ActivityLog

class ActivityLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    user_email = serializers.SerializerMethodField()
    user_role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = ActivityLog
        fields = '__all__'

    def get_user_email(self, obj):
        # If a user is linked, use their email
        if obj.user and hasattr(obj.user, 'email'):
            return obj.user.email
        # Otherwise, fall back to extra_info
        return obj.extra_info.get('email')
