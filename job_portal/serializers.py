# serializer.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    JobCategory, Skill, EmployerProfile, JobSeekerProfile, 
    Job, JobApplication, SavedJob, JobAlert, JobView
)
from authentication.serializers import UserSerializer

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'category']

class JobCategorySerializer(serializers.ModelSerializer):
    jobs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = JobCategory
        fields = ['id', 'name', 'description', 'jobs_count', 'created_at']
    
    def get_jobs_count(self, obj):
        return obj.job_set.filter(status='active').count()

class EmployerProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    total_jobs = serializers.SerializerMethodField()
    active_jobs = serializers.SerializerMethodField()
    
    class Meta:
        model = EmployerProfile
        fields = [
            'id', 'user_email', 'user_name', 'company_name', 'company_description',
            'company_website', 'company_logo', 'company_size', 'industry', 
            'location', 'phone', 'is_verified', 'total_jobs', 'active_jobs', 'created_at'
        ]
        read_only_fields = ['is_verified', 'created_at']
    
    def get_total_jobs(self, obj):
        return obj.jobs.count()
    
    def get_active_jobs(self, obj):
        return obj.jobs.filter(status='active').count()

class JobSeekerProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    total_applications = serializers.SerializerMethodField()
    
    class Meta:
        model = JobSeekerProfile
        fields = [
            'id', 'user_email', 'user_name', 'bio', 'resume', 'profile_picture',
            'phone', 'location', 'experience_years', 'skills', 'skill_ids',
            'linkedin_url', 'portfolio_url', 'expected_salary', 'is_actively_looking',
            'total_applications', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_total_applications(self, obj):
        return obj.applications.count()
    
    def update(self, instance, validated_data):
        skill_ids = validated_data.pop('skill_ids', None)
        instance = super().update(instance, validated_data)
        
        if skill_ids is not None:
            instance.skills.set(skill_ids)
        
        return instance

class JobListSerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source='employer.company_name', read_only=True)
    employer_logo = serializers.ImageField(source='employer.company_logo', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    required_skills = SkillSerializer(many=True, read_only=True)
    applications_count = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    is_saved = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'employer_name', 'employer_logo', 'location', 'is_remote',
            'job_type', 'experience_level', 'min_salary', 'max_salary', 'currency',
            'category_name', 'required_skills', 'applications_count', 'application_deadline',
            'is_expired', 'is_featured', 'views_count', 'created_at', 'is_saved', 'has_applied'
        ]
    
    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                job_seeker = request.user
                return SavedJob.objects.filter(job_seeker=job_seeker, job=obj).exists()
            except:
                return False
        return False
    
    def get_has_applied(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                job_seeker = request.user
                return JobApplication.objects.filter(applicant=job_seeker, job=obj).exists()
            except:
                return False
        return False

class JobDetailSerializer(serializers.ModelSerializer):
    employer = UserSerializer(read_only=True)
    category = JobCategorySerializer(read_only=True)
    required_skills = SkillSerializer(many=True, read_only=True)
    applications_count = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    is_saved = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()
    similar_jobs = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'description', 'requirements', 'responsibilities',
            'employer', 'category', 'required_skills', 'location', 'is_remote',
            'job_type', 'experience_level', 'min_salary', 'max_salary', 'currency',
            'benefits', 'application_deadline', 'max_applications', 'status',
            'is_featured', 'views_count', 'applications_count', 'is_expired',
            'is_saved', 'has_applied', 'similar_jobs', 'created_at', 'updated_at'
        ]
    
    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                job_seeker = request.user
                return SavedJob.objects.filter(job_seeker=job_seeker, job=obj).exists()
            except:
                return False
        return False
    
    def get_has_applied(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                job_seeker = request.user
                return JobApplication.objects.filter(applicant=job_seeker, job=obj).exists()
            except:
                return False
        return False
    
    def get_similar_jobs(self, obj):
        similar = Job.objects.filter(
            category=obj.category,
            status='active'
        ).exclude(id=obj.id)[:3]
        return JobListSerializer(similar, many=True, context=self.context).data

class JobCreateUpdateSerializer(serializers.ModelSerializer):
    required_skill_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    
    class Meta:
        model = Job
        fields = [
            'title', 'description', 'requirements', 'responsibilities',
            'category', 'required_skill_ids', 'location', 'is_remote',
            'job_type', 'experience_level', 'min_salary', 'max_salary',
            'currency', 'benefits', 'application_deadline', 'max_applications'
        ]
    
    def validate_application_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Application deadline must be in the future.")
        return value
    
    def validate(self, data):
        min_salary = data.get('min_salary')
        max_salary = data.get('max_salary')
        
        if min_salary and max_salary and min_salary > max_salary:
            raise serializers.ValidationError("Minimum salary cannot be greater than maximum salary.")
        
        return data
    
    def create(self, validated_data):
        skill_ids = validated_data.pop('required_skill_ids', [])
        employer = self.context['request'].user
        
        job = Job.objects.create(employer=employer, **validated_data)
        
        if skill_ids:
            job.required_skills.set(skill_ids)
        
        return job
    
    def update(self, instance, validated_data):
        skill_ids = validated_data.pop('required_skill_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if skill_ids is not None:
            instance.required_skills.set(skill_ids)
        
        return instance

class JobApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.user.get_full_name', read_only=True)
    applicant_email = serializers.EmailField(source='applicant.user.email', read_only=True)
    applicant_profile = JobSeekerProfileSerializer(source='applicant', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.employer.company_name', read_only=True)
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'job_title', 'company_name', 'applicant', 'applicant_name', 
            'applicant_email', 'applicant_profile', 'cover_letter', 'custom_resume',
            'status', 'employer_notes', 'interview_date', 'applied_at', 'updated_at'
        ]
        read_only_fields = ['applicant', 'applied_at', 'updated_at']

class JobApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ['job', 'cover_letter', 'custom_resume']
    
    def validate_job(self, value):
        if value.status != 'active':
            raise serializers.ValidationError("Cannot apply to inactive job.")
        
        if value.is_expired:
            raise serializers.ValidationError("Job application deadline has passed.")
        
        if value.applications_count >= value.max_applications:
            raise serializers.ValidationError("Maximum applications limit reached for this job.")
        
        return value
    
    def create(self, validated_data):
        applicant = self.context['request'].user
        return JobApplication.objects.create(applicant=applicant, **validated_data)

class SavedJobSerializer(serializers.ModelSerializer):
    job = JobListSerializer(read_only=True)
    
    class Meta:
        model = SavedJob
        fields = ['id', 'job', 'saved_at']

class JobAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAlert
        fields = [
            'id', 'title', 'keywords', 'location', 'category', 'job_type',
            'min_salary', 'is_active', 'email_frequency', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def create(self, validated_data):
        job_seeker = self.context['request'].user
        return JobAlert.objects.create(job_seeker=job_seeker, **validated_data)