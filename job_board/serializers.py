# job_board/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import JobPost, JobApplication, JobReview
from authentication.models import StudentProfile, TeacherProfile
import re


class StudentBasicSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = ['id', 'student_id', 'username', 'full_name','profile_picture']
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            # Return absolute URL for frontend usage
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None
         


class TeacherBasicSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherProfile
        fields = ['id', 'teacher_id', 'username', 'full_name','profile_picture']
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            # Return absolute URL for frontend usage
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None


class JobPostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = [
            'title', 'description', 'subject', 'teaching_mode',
            'budget_amount', 'budget_type',
            'additional_notes', 'location', 'deadline', 'time_to_study_start', 'time_to_study_end',
            'days_to_study', 'gender'
        ]
    
    def validate(self, data):

        # Validate location for physical teaching
        if data.get('teaching_mode') == 'home' and not data.get('location'):
            raise serializers.ValidationError(
                "Location is required for physical teaching mode."
            )
        
        # Validate deadline is in future
        if data.get('deadline') and data.get('deadline') <= timezone.now():
            raise serializers.ValidationError(
                "Deadline must be in the future."
            )
        
        return data

    def validate_days_to_study(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("days_to_study must be a list")
        return value

    def create(self, validated_data):
        # Set student from request user
        request = self.context.get('request')
        print(hasattr(request.user, 'student_profile'))
        if request and hasattr(request.user, 'student_profile'):
            print(request.user.student_profile)
            return JobPost.objects.create(student=request.user.student_profile, **validated_data)
        raise serializers.ValidationError("Only students can create job posts.")


class JobPostListSerializer(serializers.ModelSerializer):
    student = StudentBasicSerializer(read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPost
        fields = [
            'id', 'title', 'description', 'student', 'subject', 'current_class', 'curriculum',
            'teaching_mode', 'budget_amount', 'budget_type', 'location', 'status', 'applications_count',
            'created_at', 'time_ago', 'deadline', 'time_to_study_start', 'time_to_study_end',
            'days_to_study', 'gender'
        ]
    
    def get_time_ago(self, obj):
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"
   
class JobPostDetailSerializer(serializers.ModelSerializer):
    student = StudentBasicSerializer(read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    selected_teacher = TeacherBasicSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()
    can_apply = serializers.SerializerMethodField()
    user_application = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPost
        fields = [
            'id', 'title', 'description', 'student', 'subject',
            'teaching_mode', 'budget_amount', 'budget_type', 'additional_notes', 'location', 'status',
            'applications_count', 'selected_teacher', 'created_at', 'updated_at',
            'deadline', 'is_owner', 'can_apply', 'user_application', 'time_to_study_start', 'time_to_study_end',
            'days_to_study', 'gender'
        ]
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_profile'):
            return obj.student == request.user.student_profile
        return False

    def get_can_apply(self, obj):
        request = self.context.get("request")

        # 1. Must have request & be logged in
        if not request or not request.user.is_authenticated:
            return False

        user = request.user

        # 2. Must be a teacher
        teacher = getattr(user, "teacher_profile", None)
        if not teacher:
            return False

        # 3. Job must be open
        if obj.status != 'open':
            return False

        # 4. Student who created job cannot apply
        if obj.student.user_id == user.id:
            return False

        # 5. Teacher must not have already applied
        already_applied = obj.applications.filter(
            teacher_id=teacher.id
        ).exists()

        return not already_applied

    def get_location(self, obj):
        """
        Adds +100 to longitude in Google Maps URL
        """
        if not obj.location:
            return obj.location

        # Match latitude,longitude in URL
        match = re.search(r'([-+]?\d*\.\d+|\d+),\s*([-+]?\d*\.\d+|\d+)', obj.location)

        if not match:
            return obj.location  # fallback if format is unexpected

        lat = float(match.group(1))
        lng = float(match.group(2)) + 0.0005  # 👈 add +100 to longitude

        # Replace only the coordinates part
        new_coords = f"{lat},{lng}"
        return re.sub(r'([-+]?\d*\.\d+|\d+),\s*([-+]?\d*\.\d+|\d+)', new_coords, obj.location, count=1)
    
    def get_user_application(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'teacher_profile'):
            try:
                application = obj.applications.get(
                    teacher=request.user.teacher_profile
                )
                return JobApplicationBasicSerializer(application).data
            except JobApplication.DoesNotExist:
                pass
        return None


class JobApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = []
    
    def create(self, validated_data):
        # Set teacher and job_post from context
        request = self.context.get('request')
        job_post = self.context.get('job_post')
        
        if request and hasattr(request.user, 'teacher_profile'):
            validated_data['teacher'] = request.user.teacher_profile
        
        if job_post:
            validated_data['job_post'] = job_post
        
        return super().create(validated_data)


class JobApplicationBasicSerializer(serializers.ModelSerializer):
    teacher = TeacherBasicSerializer(read_only=True)
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            'id', 'teacher', 'status', 'applied_at', 'time_ago',
            'is_finalized', 'teacher_finalized', 'student_finalized'
        ]
        read_only_fields = ['teacher', 'status', 'applied_at', 'is_finalized']

    def get_time_ago(self, obj):
        now = timezone.now()
        diff = now - obj.applied_at

        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"


class JobApplicationDetailSerializer(serializers.ModelSerializer):
    teacher = TeacherBasicSerializer(read_only=True)
    job_post = JobPostListSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            'id', 'job_post', 'teacher', 'status', 'applied_at', 'updated_at',
            'teacher_finalized_days', 'teacher_finalized_time_start', 'teacher_finalized_time_end',
            'teacher_finalized_budget', 'teacher_demo_class_time', 'teacher_finalized',
            'student_finalized_days', 'student_finalized_time_start', 'student_finalized_time_end',
            'student_finalized_budget', 'student_demo_class_time', 'student_finalized',
            'finalized_days', 'finalized_time_start', 'finalized_time_end',
            'finalized_budget', 'demo_class_time', 'is_finalized', 'finalized_at'
        ]
        read_only_fields = ['job_post', 'teacher']


class JobApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ['status']
    
    def validate_status(self, value):
        if value not in ['accepted', 'rejected']:
            raise serializers.ValidationError(
                "Status can only be updated to 'accepted' or 'rejected'."
            )
        return value


class JobPostUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = ['status']
    
    def validate_status(self, value):
        allowed_statuses = ['in_progress', 'completed', 'cancelled']
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"Status can only be updated to: {', '.join(allowed_statuses)}"
            )
        return value


class JobReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    reviewed_name = serializers.CharField(source='reviewed.username', read_only=True)
    
    class Meta:
        model = JobReview
        fields = [
            'id', 'rating', 'comment', 'reviewer_name', 'reviewed_name', 'created_at'
        ]
        read_only_fields = ['reviewer', 'reviewed']
    
    def create(self, validated_data):
        request = self.context.get('request')
        job_post = self.context.get('job_post')
        
        if request:
            validated_data['reviewer'] = request.user
            # Set reviewed user based on who's reviewing
            if hasattr(request.user, 'student_profile'):
                # Student reviewing teacher
                validated_data['reviewed'] = job_post.selected_teacher.user
            else:
                # Teacher reviewing student
                validated_data['reviewed'] = job_post.student.user
        
        validated_data['job_post'] = job_post
        return super().create(validated_data)


# Dashboard serializers for overview
class MyJobPostSerializer(serializers.ModelSerializer):
    applications_count = serializers.IntegerField(read_only=True)
    selected_teacher = TeacherBasicSerializer(read_only=True)
    
    class Meta:
        model = JobPost
        fields = [
            'id', 'title', 'subject', 'status',
            'applications_count', 'selected_teacher', 'created_at',
            'budget_amount', 'budget_type', 'days_to_study', 'curriculum', 'current_class',
            'time_to_study_start', 'time_to_study_end', 'teaching_mode', 'location',
        ]


class MyJobApplicationSerializer(serializers.ModelSerializer):
    job_post = JobPostListSerializer(read_only=True)
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job_post', 'status', 'applied_at',
            'is_finalized', 'teacher_finalized', 'student_finalized'
        ]