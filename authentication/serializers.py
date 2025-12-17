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

    # location
    address = serializers.CharField(required=False, allow_null=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True, required=False)

    # Academic Info/Preferences
    preferred_learning_time = serializers.JSONField(required=False, allow_null=True)
    language_preferences = serializers.JSONField(required=False, allow_null=True)
    member_since = serializers.DateTimeField(source='user.date_joined', read_only=True)

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data):
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)

        if latitude is not None and longitude is not None:
            validated_data["location"] = (
                f"https://www.google.com/maps?q={latitude},{longitude}"
            )

        return super().create(validated_data)

    class Meta:
        model = StudentProfile
        exclude = ['created_at', 'updated_at', 'is_active']
        read_only_fields = [
            'user', 'email', 'student_id',
            'completed_courses_count', 'current_courses_count',
            'attendance_percentage', 'completed_assignments',
            'average_course_rating'
        ]

    # def validate_preferred_learning_time(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Preferred learning time must be a list")
    #     return value

    # def validate_language_preferences(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Language preferences must be a list")
    #     return value

class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    country = serializers.CharField(required=True)
    city = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    date_of_birth = serializers.DateField(required=True)
    gender = serializers.CharField(required=True)
    identity_no = serializers.CharField(required=True)

    # location
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True, required=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True, required=True)

    teaching_mode = serializers.CharField(required=True)
    subjects = serializers.JSONField(required=True)
    curriculum = serializers.JSONField(required=True)
    classes = serializers.JSONField(required=True)
    years_of_experience = serializers.IntegerField(min_value=0, required=True)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    headline = serializers.CharField(required=True)

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data):
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)

        if latitude is not None and longitude is not None:
            validated_data["location"] = (
                f"https://www.google.com/maps?q={latitude},{longitude}"
            )

        return super().create(validated_data)

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

    # def validate_education(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Education must be a list")
    #     for edu in value:
    #         if not isinstance(edu, dict) or not all(k in edu for k in ['degree', 'institution', 'year']):
    #             raise serializers.ValidationError("Each education entry must contain degree, institution, and year")
    #     return value

    # def validate_languages_spoken(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Languages spoken must be a list")
    #     return value

    # def validate_availability_schedule(self, value):
    #     if not isinstance(value, dict):
    #         raise serializers.ValidationError("Availability schedule must be a dictionary")
    #     return value

    # def validate_preferred_teaching_methods(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Preferred teaching methods must be a list")
    #     return value

    # def validate_social_links(self, value):
    #     if not isinstance(value, dict):
    #         raise serializers.ValidationError("Social links must be a dictionary")
    #     return value


class StudentQuerySerializer(serializers.ModelSerializer):
    """
    Serializer for Student Query Form
    """
    # location
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True, required=False)

    class Meta:
        model = StudentQuery
        fields = [
            'id', 'full_name', 'email', 'phone', 'tutor_gender', 'city', 'country', 'address', 'curriculum',
            'learning_mode', 'current_class', 'subjects', 'special_requirements', 'location', 'latitude',
            'longitude', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data):
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)

        if latitude is not None and longitude is not None:
            validated_data["location"] = (
                f"https://www.google.com/maps?q={latitude},{longitude}"
            )
        return super().create(validated_data)

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
