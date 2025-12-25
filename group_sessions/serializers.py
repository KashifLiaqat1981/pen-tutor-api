# group_sessions/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from authentication.models import TeacherProfile
from .models import GroupSession, GroupSessionEnrollment
from meetings.serializers import MeetingSerializer
from django.utils import timezone

User = get_user_model()


class GroupSessionSerializer(serializers.ModelSerializer):
    """Serializer for Group Session details"""
    teacher = serializers.SerializerMethodField()
    teacher_id = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    meeting = MeetingSerializer(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    is_live = serializers.BooleanField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    seats_remaining = serializers.IntegerField(read_only=True)
    student_enrollment_status = serializers.SerializerMethodField()
    can_enroll = serializers.SerializerMethodField()

    class Meta:
        model = GroupSession
        fields = [
            'id', 'title', 'description', 'short_description', 'profile_picture',
            'teacher', 'teacher_id', 'subject', 'tags', 'starting_date', 'days',
            'start_time', 'class_duration', 'session_duration',
            'max_students', 'min_students', 'current_enrollments',
            'price', 'is_free', 'currency',
            'meeting', 'status', 'is_featured', 'is_private',
            'created_at', 'updated_at', 'published_at',
            'is_upcoming', 'is_live', 'is_available', 'seats_remaining',
            'student_enrollment_status', 'can_enroll'
        ]
        read_only_fields = [
            'id', 'teacher', 'current_enrollments', 'meeting',
            'created_at', 'updated_at', 'published_at',
            'is_upcoming', 'is_live', 'is_available', 'seats_remaining'
        ]

    def get_teacher(self, obj):
        return {
            'id': obj.teacher.id,
            'name': obj.teacher.get_full_name() or obj.teacher.username,
            'email': obj.teacher.email
        }

    def get_teacher_id(self, obj):
        """Return teacher_id from TeacherProfile if it exists"""
        try:
            return obj.teacher.teacher_profile.teacher_id
        except TeacherProfile.DoesNotExist:
            return None

    def get_profile_picture(self, obj):
        """Return teacher_profile_picture from TeacherProfile if it exists"""
        profile = getattr(obj.teacher, 'teacher_profile', None)
        if profile and profile.profile_picture:
            return self.context['request'].build_absolute_uri(profile.profile_picture.url)
        return None

    def get_student_enrollment_status(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            enrollment = GroupSessionEnrollment.objects.filter(
                session=obj,
                student=request.user
            ).first()
            if enrollment:
                return {
                    'status': enrollment.status,
                    'enrolled_at': enrollment.enrolled_at,
                    'payment_status': 'paid' if enrollment.payment else 'pending'
                }
        return None

    def get_can_enroll(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            can_enroll, message = obj.can_student_join(request.user)
            return {'can_enroll': can_enroll, 'message': message}
        return {'can_enroll': False, 'message': 'Authentication required'}


class CreateGroupSessionSerializer(serializers.ModelSerializer):
    """Serializer for creating group sessions"""

    class Meta:
        model = GroupSession
        fields = [
            'title', 'description', 'short_description',
            'subject', 'tags', 'starting_date', 'days',
            'start_time', 'class_duration', 'session_duration',
            'max_students', 'min_students',
            'price', 'is_free', 'currency',
            'is_private', 'requires_approval',
        ]

    def validate(self, data):
        # Ensure start time is in future
        if data['start_time'] <= timezone.now():
            raise serializers.ValidationError({
                'start_time': 'Start time must be in the future'
            })

        # Validate max students
        if data['max_students'] < data['min_students']:
            raise serializers.ValidationError({
                'max_students': 'Maximum students cannot be less than minimum students'
            })

        # For free sessions, price should be 0
        if data.get('is_free', False) and data.get('price', 0) > 0:
            raise serializers.ValidationError({
                'price': 'Free sessions must have price 0'
            })

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['teacher'] = request.user
        validated_data['status'] = 'draft'
        return super().create(validated_data)


class UpdateGroupSessionSerializer(serializers.ModelSerializer):
    """Serializer for updating group sessions"""

    class Meta:
        model = GroupSession
        fields = [
            'title', 'description', 'short_description',
            'teacher', 'subject', 'tags', 'starting_date', 'days',
            'start_time', 'class_duration', 'session_duration',
            'max_students', 'min_students',
            'price', 'is_free', 'currency',
            'is_private', 'requires_approval',
            'status'  # For publishing/cancelling
        ]
        read_only_fields = ['status']  # Can be updated via specific endpoints

    def validate(self, data):
        instance = self.instance

        # Don't allow changing start time if session is published
        if instance.status == 'published' and 'start_time' in data:
            if data['start_time'] != instance.start_time:
                raise serializers.ValidationError({
                    'start_time': 'Cannot change start time of published session'
                })

        # Don't allow changing price if there are enrollments
        if instance.current_enrollments > 0 and 'price' in data:
            if data['price'] != instance.price:
                raise serializers.ValidationError({
                    'price': 'Cannot change price when there are enrollments'
                })

        return data


class EnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for session enrollments"""
    session = GroupSessionSerializer(read_only=True)
    student = serializers.SerializerMethodField()
    can_join_meeting = serializers.BooleanField(read_only=True)

    class Meta:
        model = GroupSessionEnrollment
        fields = [
            'id', 'session', 'student', 'status',
            'enrolled_at', 'cancelled_at', 'completed_at',
            'payment', 'attended',
            'attendance_duration', 'rating', 'review',
            'reviewed_at', 'can_join_meeting'
        ]
        read_only_fields = [
            'id', 'session', 'student', 'enrolled_at',
            'cancelled_at', 'completed_at', 'payment',
            'joined_at', 'left_at', 'attendance_duration',
            'reviewed_at', 'can_join_meeting'
        ]

    def get_student(self, obj):
        return {
            'id': obj.student.id,
            'name': obj.student.get_full_name() or obj.student.username,
            'email': obj.student.email
        }


class CreateEnrollmentSerializer(serializers.Serializer):
    """Serializer for creating enrollments"""
    session_id = serializers.UUIDField(required=True)

    def validate(self, data):
        request = self.context.get('request')
        session_id = data['session_id']

        try:
            session = GroupSession.objects.get(id=session_id)
        except GroupSession.DoesNotExist:
            raise serializers.ValidationError({
                'session_id': 'Group session not found'
            })

        # Check if session is available
        if not session.is_available:
            raise serializers.ValidationError({
                'session': 'Session is not available for enrollment'
            })

        # Check if student can join
        can_join, message = session.can_student_join(request.user)
        if not can_join:
            raise serializers.ValidationError({
                'session': message
            })

        # Check for existing enrollment
        if GroupSessionEnrollment.objects.filter(
                session=session,
                student=request.user
        ).exists():
            raise serializers.ValidationError({
                'session': 'You are already enrolled or have a pending enrollment'
            })

        data['session'] = session
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        session = validated_data['session']

        status = 'pending' if session.requires_approval else 'enrolled'

        enrollment = GroupSessionEnrollment.objects.create(
            session=session,
            student=request.user,
            status=status
        )

        return enrollment
