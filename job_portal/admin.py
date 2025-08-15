from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    JobCategory, Skill, EmployerProfile, JobSeekerProfile, 
    Job, JobApplication, SavedJob, JobAlert, JobView
)

@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'jobs_count', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at']
    
    def jobs_count(self, obj):
        return obj.job_set.count()
    jobs_count.short_description = 'Total Jobs'

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    list_filter = ['category']
    search_fields = ['name', 'category']

@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user_email', 'industry', 'location', 'is_verified', 'jobs_count', 'created_at']
    list_filter = ['is_verified', 'industry', 'company_size', 'created_at']
    search_fields = ['company_name', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'user_link']
    actions = ['verify_employers', 'unverify_employers']
    
    fieldsets = (
        ('Company Information', {
            'fields': ('user_link', 'company_name', 'company_description', 'company_website', 'company_logo')
        }),
        ('Company Details', {
            'fields': ('company_size', 'industry', 'location', 'phone')
        }),
        ('Status', {
            'fields': ('is_verified', 'created_at')
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def jobs_count(self, obj):
        return obj.jobs.count()
    jobs_count.short_description = 'Total Jobs'
    
    def verify_employers(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f'{queryset.count()} employers verified successfully.')
    verify_employers.short_description = 'Verify selected employers'
    
    def unverify_employers(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, f'{queryset.count()} employers unverified.')
    unverify_employers.short_description = 'Unverify selected employers'

@admin.register(JobSeekerProfile)
class JobSeekerProfileAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'user_email', 'location', 'experience_years', 'is_actively_looking', 'applications_count', 'created_at']
    list_filter = ['is_actively_looking', 'experience_years', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'location']
    readonly_fields = ['created_at', 'user_link']
    filter_horizontal = ['skills']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('user_link', 'bio', 'profile_picture', 'phone', 'location')
        }),
        ('Professional Details', {
            'fields': ('resume', 'experience_years', 'skills', 'expected_salary')
        }),
        ('Online Presence', {
            'fields': ('linkedin_url', 'portfolio_url')
        }),
        ('Status', {
            'fields': ('is_actively_looking', 'created_at')
        }),
    )
    
    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = 'Name'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def applications_count(self, obj):
        return obj.applications.count()
    applications_count.short_description = 'Applications'

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company_name', 'location', 'job_type', 'status', 'is_featured', 'applications_count', 'views_count', 'created_at']
    list_filter = ['status', 'job_type', 'experience_level', 'is_remote', 'is_featured', 'created_at', 'category']
    search_fields = ['title', 'employer__company_name', 'location', 'description']
    readonly_fields = ['created_at', 'updated_at', 'views_count', 'applications_count', 'employer_link']
    filter_horizontal = ['required_skills']
    actions = ['activate_jobs', 'deactivate_jobs', 'feature_jobs', 'unfeature_jobs']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('employer_link', 'title', 'description', 'category')
        }),
        ('Job Details', {
            'fields': ('requirements', 'responsibilities', 'required_skills', 'benefits')
        }),
        ('Location & Type', {
            'fields': ('location', 'is_remote', 'job_type', 'experience_level')
        }),
        ('Salary & Limits', {
            'fields': ('min_salary', 'max_salary', 'currency', 'max_applications')
        }),
        ('Timing', {
            'fields': ('application_deadline',)
        }),
        ('Status & Features', {
            'fields': ('status', 'is_featured')
        }),
        ('Statistics', {
            'fields': ('views_count', 'applications_count', 'created_at', 'updated_at')
        }),
    )
    
    def company_name(self, obj):
        return getattr(obj.employer, 'company_name', 'N/A')
    company_name.short_description = 'Company'
    
    def employer_link(self, obj):
        if obj.employer:
            url = reverse('admin:job_board_employerprofile_change', args=[obj.employer.id])
            return format_html('<a href="{}">{}</a>', url, obj.employer.company_name)
        return '-'
    employer_link.short_description = 'Employer'
    
    def activate_jobs(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, f'{queryset.count()} jobs activated successfully.')
    activate_jobs.short_description = 'Activate selected jobs'
    
    def deactivate_jobs(self, request, queryset):
        queryset.update(status='closed')
        self.message_user(request, f'{queryset.count()} jobs deactivated.')
    deactivate_jobs.short_description = 'Deactivate selected jobs'
    
    def feature_jobs(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f'{queryset.count()} jobs featured successfully.')
    feature_jobs.short_description = 'Feature selected jobs'
    
    def unfeature_jobs(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f'{queryset.count()} jobs unfeatured.')
    unfeature_jobs.short_description = 'Unfeature selected jobs'

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant_name', 'job_title', 'company_name', 'status', 'applied_at']
    list_filter = ['status', 'applied_at', 'job__job_type', 'job__category']
    search_fields = ['applicant__user__first_name', 'applicant__user__last_name', 'applicant__user__email', 'job__title', 'job__employer__company_name']
    readonly_fields = ['applied_at', 'updated_at', 'job_link', 'applicant_link']
    actions = ['mark_as_reviewed', 'mark_as_shortlisted', 'mark_as_rejected']
    date_hierarchy = 'applied_at'
    
    fieldsets = (
        ('Application Details', {
            'fields': ('job_link', 'applicant_link', 'cover_letter', 'custom_resume')
        }),
        ('Status & Notes', {
            'fields': ('status', 'employer_notes', 'interview_date')
        }),
        ('Timestamps', {
            'fields': ('applied_at', 'updated_at')
        }),
    )
    
    def applicant_name(self, obj):
        return obj.applicant.user.get_full_name() or obj.applicant.user.username
    applicant_name.short_description = 'Applicant'
    
    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Job'
    
    def company_name(self, obj):
        employer = getattr(obj.job, 'employer', None)
        return getattr(employer, 'company_name', 'N/A') if employer else 'N/A'
    company_name.short_description = 'Company'
    
    def job_link(self, obj):
        if obj.job:
            url = reverse('admin:job_board_job_change', args=[obj.job.id])
            return format_html('<a href="{}">{}</a>', url, obj.job.title)
        return '-'
    job_link.short_description = 'Job'
    
    def applicant_link(self, obj):
        if obj.applicant:
            url = reverse('admin:job_board_jobseekerprofile_change', args=[obj.applicant.id])
            return format_html('<a href="{}">{}</a>', url, obj.applicant.user.get_full_name() or obj.applicant.user.username)
        return '-'
    applicant_link.short_description = 'Applicant'
    
    def mark_as_reviewed(self, request, queryset):
        queryset.update(status='reviewed')
        self.message_user(request, f'{queryset.count()} applications marked as reviewed.')
    mark_as_reviewed.short_description = 'Mark as reviewed'
    
    def mark_as_shortlisted(self, request, queryset):
        queryset.update(status='shortlisted')
        self.message_user(request, f'{queryset.count()} applications shortlisted.')
    mark_as_shortlisted.short_description = 'Mark as shortlisted'
    
    def mark_as_rejected(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} applications rejected.')
    mark_as_rejected.short_description = 'Mark as rejected'

@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ['job_seeker_name', 'job_title', 'company_name', 'saved_at']
    list_filter = ['saved_at', 'job__job_type', 'job__category']
    search_fields = ['job_seeker__user__first_name', 'job_seeker__user__last_name', 'job__title', 'job__employer__company_name']
    readonly_fields = ['saved_at']
    
    def job_seeker_name(self, obj):
        return obj.job_seeker.user.get_full_name() or obj.job_seeker.user.username
    job_seeker_name.short_description = 'Job Seeker'
    
    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Job'
    
    def company_name(self, obj):
        employer = getattr(obj.job, 'employer', None)
        return getattr(employer, 'company_name', 'N/A') if employer else 'N/A'
    company_name.short_description = 'Company'

@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ['job_seeker_name', 'title', 'location', 'job_type', 'is_active', 'email_frequency', 'created_at']
    list_filter = ['is_active', 'job_type', 'email_frequency', 'created_at']
    search_fields = ['job_seeker__user__first_name', 'job_seeker__user__last_name', 'title', 'keywords', 'location']
    readonly_fields = ['created_at']
    
    def job_seeker_name(self, obj):
        return obj.job_seeker.user.get_full_name() or obj.job_seeker.user.username
    job_seeker_name.short_description = 'Job Seeker'

@admin.register(JobView)
class JobViewAdmin(admin.ModelAdmin):
    list_display = ['job_title', 'company_name', 'user_name', 'ip_address', 'viewed_at']
    list_filter = ['viewed_at', 'job__job_type', 'job__category']
    search_fields = ['job__title', 'job__employer__company_name', 'user__first_name', 'user__last_name', 'ip_address']
    readonly_fields = ['viewed_at']
    
    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Job'
    
    def company_name(self, obj):
        employer = getattr(obj.job, 'employer', None)
        return getattr(employer, 'company_name', 'N/A') if employer else 'N/A'
    company_name.short_description = 'Company'
    
    def user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'Anonymous'
    user_name.short_description = 'User'

# Custom admin site configuration
admin.site.site_header = "Job Board Administration"
admin.site.site_title = "Job Board Admin"
admin.site.index_title = "Welcome to Job Board Administration"