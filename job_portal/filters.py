import django_filters
from django.db.models import Q
from .models import Job, JobCategory, Skill

class JobFilter(django_filters.FilterSet):
    # Basic filters
    category = django_filters.ModelChoiceFilter(
        queryset=JobCategory.objects.all(),
        field_name='category'
    )
    
    job_type = django_filters.ChoiceFilter(
        choices=Job.JOB_TYPE_CHOICES,
        field_name='job_type'
    )
    
    experience_level = django_filters.ChoiceFilter(
        choices=Job.EXPERIENCE_LEVEL_CHOICES,
        field_name='experience_level'
    )
    
    is_remote = django_filters.BooleanFilter(field_name='is_remote')
    is_featured = django_filters.BooleanFilter(field_name='is_featured')
    
    # Location filters
    location = django_filters.CharFilter(
        field_name='location',
        lookup_expr='icontains'
    )
    
    # Salary filters
    min_salary = django_filters.NumberFilter(
        field_name='min_salary',
        lookup_expr='gte'
    )
    
    max_salary = django_filters.NumberFilter(
        field_name='max_salary',
        lookup_expr='lte'
    )
    
    salary_range = django_filters.RangeFilter(field_name='min_salary')
    
    # Skills filter
    skills = django_filters.ModelMultipleChoiceFilter(
        queryset=Skill.objects.all(),
        field_name='required_skills',
        conjoined=False  # OR condition instead of AND
    )
    
    # Company filter
    company = django_filters.CharFilter(
        field_name='employer__company_name',
        lookup_expr='icontains'
    )
    
    # Date filters
    posted_within = django_filters.NumberFilter(
        method='filter_posted_within'
    )
    
    deadline_within = django_filters.NumberFilter(
        method='filter_deadline_within'
    )
    
    # Custom search filter
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Job
        fields = [
            'category', 'job_type', 'experience_level', 'is_remote', 
            'is_featured', 'location', 'min_salary', 'max_salary',
            'skills', 'company'
        ]
    
    def filter_posted_within(self, queryset, name, value):
        """Filter jobs posted within X days"""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            
            cutoff_date = timezone.now() - timedelta(days=value)
            return queryset.filter(created_at__gte=cutoff_date)
        return queryset
    
    def filter_deadline_within(self, queryset, name, value):
        """Filter jobs with deadline within X days"""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            
            cutoff_date = timezone.now() + timedelta(days=value)
            return queryset.filter(application_deadline__lte=cutoff_date)
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Custom search across multiple fields"""
        if value:
            return queryset.filter(
                Q(title__icontains=value) |
                Q(description__icontains=value) |
                Q(employer__company_name__icontains=value) |
                Q(location__icontains=value) |
                Q(required_skills__name__icontains=value)
            ).distinct()
        return queryset