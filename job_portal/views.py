from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg
from django.utils import timezone



from .models import (
    JobCategory, Skill, EmployerProfile, JobSeekerProfile, 
    Job, JobApplication, SavedJob, JobAlert, JobView
)
from .serializers import (
    JobCategorySerializer, SkillSerializer, EmployerProfileSerializer,
    JobSeekerProfileSerializer, JobListSerializer, JobDetailSerializer,
    JobCreateUpdateSerializer, JobApplicationSerializer, JobApplicationCreateSerializer,
    SavedJobSerializer, JobAlertSerializer
)
from .filters import JobFilter
from .permissions import IsEmployerOrReadOnly, IsJobSeekerOrReadOnly, IsOwnerOrReadOnly

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# =============== CATEGORY & SKILLS APIS ===============
class JobCategoryListView(generics.ListCreateAPIView):
    queryset = JobCategory.objects.all()
    serializer_class = JobCategorySerializer
    permission_classes = [AllowAny]

class SkillListView(generics.ListCreateAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category']

# =============== PROFILE APIS ===============
class EmployerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = EmployerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = EmployerProfile.objects.get_or_create(user=self.request.user)
        return profile

class JobSeekerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = JobSeekerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = JobSeekerProfile.objects.get_or_create(user=self.request.user)
        return profile

# =============== JOB APIS ===============
class JobListView(generics.ListAPIView):
    serializer_class = JobListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JobFilter
    search_fields = ['title', 'description', 'employer__company_name', 'location']
    ordering_fields = ['created_at', 'application_deadline', 'min_salary']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Job.objects.filter(status='active').select_related(
            'employer', 'category'
        ).prefetch_related('required_skills')
        
        # Featured jobs first
        return queryset.order_by('-is_featured', '-created_at')

class JobDetailView(generics.RetrieveAPIView):
    serializer_class = JobDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Job.objects.select_related('employer', 'category').prefetch_related('required_skills')
    
    def retrieve(self, request, *args, **kwargs):
        job = self.get_object()
        
        # Track job view
        if request.user.is_authenticated or request.META.get('REMOTE_ADDR'):
            JobView.objects.get_or_create(
                job=job,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            # Increment view count
            Job.objects.filter(id=job.id).update(views_count=job.views_count + 1)
        
        serializer = self.get_serializer(job)
        return Response(serializer.data)

class EmployerJobListView(generics.ListCreateAPIView):
    serializer_class = JobListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Job.objects.filter(
            employer=self.request.user
        ).select_related('employer', 'category').prefetch_related('required_skills')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JobCreateUpdateSerializer
        return JobListSerializer

class EmployerJobDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Job.objects.filter(employer__user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return JobCreateUpdateSerializer
        return JobDetailSerializer

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_job_status(request, job_id):
    """Update job status (draft/active/closed)"""
    try:
        job = Job.objects.get(id=job_id, employer=request.user)
    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    new_status = request.data.get('status')
    if new_status not in ['draft', 'active', 'closed']:
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    job.status = new_status
    job.save()
    
    return Response({'message': f'Job status updated to {new_status}'})

# =============== JOB APPLICATION APIS ===============
class JobApplicationListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        if hasattr(self.request.user, 'jobseeker_profile'):
            # Job seeker sees their applications
            return JobApplication.objects.filter(
                applicant=self.request.user.jobseeker_profile
            ).select_related('job', 'job__employer')
        elif hasattr(self.request.user, 'employer_profile'):
            # Employer sees applications to their jobs
            return JobApplication.objects.filter(
                job__employer=self.request.user.employer_profile
            ).select_related('job', 'applicant', 'applicant__user')
        return JobApplication.objects.none()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JobApplicationCreateSerializer
        return JobApplicationSerializer

class JobApplicationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return JobApplication.objects.filter(applicant=self.request.user)
        # if hasattr(self.request.user, 'jobseeker_profile'):
        #     return JobApplication.objects.filter(applicant=self.request.user)
        # elif hasattr(self.request.user, 'employer_profile'):
        #     return JobApplication.objects.filter(job__employer=self.request.user)
        # return JobApplication.objects.none()

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_application_status(request, application_id):
    """Employer updates application status"""
    try:
        if hasattr(request.user, 'employer_profile'):
            application = JobApplication.objects.get(
                id=application_id, 
                job__employer=request.user.employer_profile
            )
        else:
            return Response({'error': 'Only employers can update application status'}, 
                          status=status.HTTP_403_FORBIDDEN)
    except JobApplication.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
    
    new_status = request.data.get('status')
    valid_statuses = ['pending', 'reviewed', 'shortlisted', 'interview_scheduled', 'rejected', 'accepted']
    
    if new_status not in valid_statuses:
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    application.status = new_status
    application.employer_notes = request.data.get('employer_notes', application.employer_notes)
    application.interview_date = request.data.get('interview_date', application.interview_date)
    application.save()
    
    return Response({
        'message': f'Application status updated to {new_status}',
        'application': JobApplicationSerializer(application).data
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def withdraw_application(request, application_id):
    """Job seeker withdraws application"""
    try:
        application = JobApplication.objects.get(
            id=application_id, 
            applicant=request.user.jobseeker_profile
        )
    except JobApplication.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if application.status in ['accepted', 'rejected']:
        return Response({'error': 'Cannot withdraw application that is already processed'}, 
                      status=status.HTTP_400_BAD_REQUEST)
    
    application.status = 'withdrawn'
    application.save()
    
    return Response({'message': 'Application withdrawn successfully'})

# =============== SAVED JOBS APIS ===============
class SavedJobListView(generics.ListAPIView):
    serializer_class = SavedJobSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return SavedJob.objects.filter(
            job_seeker=self.request.user.jobseeker_profile
        ).select_related('job', 'job__employer', 'job__category')

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def toggle_save_job(request, job_id):
    """Save or unsave a job"""
    try:
        job = Job.objects.get(id=job_id, status='active')
        job_seeker = request.user.jobseeker_profile
    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'POST':
        saved_job, created = SavedJob.objects.get_or_create(
            job_seeker=job_seeker, 
            job=job
        )
        if created:
            return Response({'message': 'Job saved successfully', 'saved': True})
        else:
            return Response({'message': 'Job already saved', 'saved': True})
    
    elif request.method == 'DELETE':
        try:
            saved_job = SavedJob.objects.get(job_seeker=job_seeker, job=job)
            saved_job.delete()
            return Response({'message': 'Job removed from saved list', 'saved': False})
        except SavedJob.DoesNotExist:
            return Response({'message': 'Job was not saved', 'saved': False})

# =============== JOB ALERTS APIS ===============
class JobAlertListView(generics.ListCreateAPIView):
    serializer_class = JobAlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return JobAlert.objects.filter(job_seeker=self.request.user.jobseeker_profile)

class JobAlertDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobAlertSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return JobAlert.objects.filter(job_seeker=self.request.user.jobseeker_profile)

# =============== RECOMMENDATION & SEARCH APIS ===============
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommended_jobs(request):
    """Get personalized job recommendations"""
    job_seeker = request.user.jobseeker_profile
    user_skills = job_seeker.skills.all()
    
    if not user_skills.exists():
        # If no skills, return recent jobs
        recommended_jobs = Job.objects.filter(status='active')[:10]
    else:
        # Find jobs matching user skills
        recommended_jobs = Job.objects.filter(
            status='active',
            required_skills__in=user_skills
        ).annotate(
            skill_match_count=Count('required_skills', filter=Q(required_skills__in=user_skills))
        ).order_by('-skill_match_count', '-created_at')[:10]
    
    serializer = JobListSerializer(recommended_jobs, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def get_job_stats(request):
    """Get job board statistics"""
    stats = {
        'total_jobs': Job.objects.filter(status='active').count(),
        'total_companies': EmployerProfile.objects.filter(is_verified=True).count(),
        'total_applications': JobApplication.objects.count(),
        'jobs_by_type': Job.objects.filter(status='active').values('job_type').annotate(count=Count('id')),
        'jobs_by_category': Job.objects.filter(status='active').values(
            'category__name'
        ).annotate(count=Count('id')),
        'recent_jobs_count': Job.objects.filter(
            status='active',
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
    }
    return Response(stats)

@api_view(['GET'])
def search_suggestions(request):
    """Get search suggestions for autocomplete"""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return Response([])
    
    # Search in job titles, company names, and locations
    job_titles = Job.objects.filter(
        status='active',
        title__icontains=query
    ).values_list('title', flat=True).distinct()[:5]
    
    company_names = EmployerProfile.objects.filter(
        company_name__icontains=query
    ).values_list('company_name', flat=True).distinct()[:5]
    
    locations = Job.objects.filter(
        status='active',
        location__icontains=query
    ).values_list('location', flat=True).distinct()[:5]
    
    suggestions = {
        'job_titles': list(job_titles),
        'companies': list(company_names),
        'locations': list(locations)
    }
    
    return Response(suggestions)

# =============== ADMIN APIS ===============
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_stats(request):
    """Admin dashboard statistics"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    stats = {
        'total_jobs': Job.objects.count(),
        'active_jobs': Job.objects.filter(status='active').count(),
        'pending_jobs': Job.objects.filter(status='pending').count(),
        'total_applications': JobApplication.objects.count(),
        'total_employers': EmployerProfile.objects.count(),
        'verified_employers': EmployerProfile.objects.filter(is_verified=True).count(),
        'total_job_seekers': JobSeekerProfile.objects.count(),
        'recent_jobs': Job.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count(),
        'recent_applications': JobApplication.objects.filter(
            applied_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
    }
    
    return Response(stats)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_moderate_job(request, job_id):
    """Admin approve/reject/block job"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    action = request.data.get('action')  # 'approve', 'block', 'feature'
    
    if action == 'approve':
        job.status = 'active'
    elif action == 'block':
        job.status = 'blocked'
    elif action == 'feature':
        job.is_featured = not job.is_featured
    else:
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
    
    job.save()
    
    return Response({
        'message': f'Job {action}d successfully',
        'job': JobDetailSerializer(job).data
    })

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_verify_employer(request, employer_id):
    """Admin verify/unverify employer"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        employer = EmployerProfile.objects.get(id=employer_id)
    except EmployerProfile.DoesNotExist:
        return Response({'error': 'Employer not found'}, status=status.HTTP_404_NOT_FOUND)
    
    employer.is_verified = not employer.is_verified
    employer.save()
    
    return Response({
        'message': f'Employer {"verified" if employer.is_verified else "unverified"} successfully',
        'employer': EmployerProfileSerializer(employer).data
    })