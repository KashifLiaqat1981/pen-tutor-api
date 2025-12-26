# authentication/serializers.py

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, StudentProfile, TeacherProfile, StudentQuery

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            if not user.is_verified:
                raise serializers.ValidationError('Please verify your email first.')
            attrs['user'] = user
        return attrs

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'created_at']
        read_only_fields = ['id', 'created_at', 'is_verified']

class RoleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['role']

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    country = serializers.CharField(required=True)
    city = serializers.CharField(required=True)
    curriculum = serializers.CharField(required=True)
    current_class = serializers.CharField(required=True)
    tutor_gender = serializers.CharField(required=True)
    learning_mode = serializers.CharField(required=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)
    # Academic Info/Preferences
    preferred_learning_time = serializers.JSONField(required=False, allow_null=True)
    language_preferences = serializers.JSONField(required=False, allow_null=True)
    member_since = serializers.DateTimeField(source='user.date_joined', read_only=True)

    class Meta:
        model = StudentProfile
        exclude = ['created_at', 'updated_at', 'is_active']
        read_only_fields = [
            'user', 'email', 'student_id',
            'completed_courses_count', 'current_courses_count',
            'attendance_percentage', 'completed_assignments',
            'average_course_rating'
        ]

    def validate_preferred_learning_time(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Preferred learning time must be a list")
        return value

    def validate_language_preferences(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Language preferences must be a list")
        return value

class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    address = serializers.CharField(required=False)
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.CharField(required=False)
    identity_no = serializers.CharField(required=False)

    teaching_mode = serializers.CharField(required=False)
    subjects = serializers.JSONField(required=False)
    curriculum = serializers.JSONField(required=False)
    classes = serializers.JSONField(required=False)
    years_of_experience = serializers.IntegerField(min_value=0, required=False)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    headline = serializers.CharField(required=False)
    is_profile_complete = serializers.ReadOnlyField()
    profile_completion_percentage = serializers.ReadOnlyField()
    languages_spoken = serializers.JSONField(required=False)
    availability_schedule = serializers.JSONField(required=False)
    social_links = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = TeacherProfile
        exclude = ['created_at', 'updated_at', 'is_active']
        read_only_fields = [
            'user', 'email', 'teacher_id',
            'total_courses', 'total_students',
            'average_rating', 'total_course_hours',
            'total_students_helped', 'response_rate',
            'average_response_time','is_profile_complete',
            'profile_completion_percentage'
        ]

    def validate_languages_spoken(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Languages spoken must be a list")
        return value

    def validate_availability_schedule(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Availability schedule must be a list")
        return value


class PublicTeacherSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = TeacherProfile
        fields = [
            "user_id", "teacher_id", "headline", "profile_picture", "subjects", "curriculum",
            "classes", "years_of_experience", "hourly_rate", "currency", "languages_spoken",
            'country', 'city', 'teaching_mode', 'availability_schedule', 'education', 'gender'
        ]


class StudentQuerySerializer(serializers.ModelSerializer):
    """
    Serializer for Student Query Form
    """
    class Meta:
        model = StudentQuery
        fields = [
            'id', 'full_name', 'email', 'phone', 'tutor_gender', 'city', 'country', 'address', 'curriculum',
            'learning_mode', 'current_class', 'subjects', 'special_requirements', 'location', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_email(self, value):
        """Validate email format"""
        return value.lower()

    def validate_subjects(self, value):
        """Clean subjects field"""
        if isinstance(value, str):
            value = value.split(",")
        return [s.strip() for s in value if s.strip()]


class StudentQueryListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing student queries in admin dashboard
    """
    linked_user_email = serializers.CharField(source='linked_user.email', read_only=True)
    
    class Meta:
        model = StudentQuery
        fields = [
            'id', 'full_name', 'email', 'phone', 'address',
            'current_class', 'subjects', 'special_requirements',
            'is_registered', 'is_processed', 'admin_notes',
            'linked_user_email', 'created_at', 'updated_at'

        ]
