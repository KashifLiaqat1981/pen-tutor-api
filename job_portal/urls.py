from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'job_board'

urlpatterns = [
    # =============== CATEGORY & SKILLS ===============
    path('categories/', views.JobCategoryListView.as_view(), name='job-categories'),
    path('skills/', views.SkillListView.as_view(), name='skills'),
    
    # =============== PROFILES ===============
    path('profile/employer/', views.EmployerProfileView.as_view(), name='employer-profile'),
    path('profile/jobseeker/', views.JobSeekerProfileView.as_view(), name='jobseeker-profile'),
    
    # =============== JOBS - PUBLIC ===============
    path('jobs/', views.JobListView.as_view(), name='job-list'),
    path('jobs/<int:id>/', views.JobDetailView.as_view(), name='job-detail'),
    path('jobs/stats/', views.get_job_stats, name='job-stats'),
    path('jobs/search-suggestions/', views.search_suggestions, name='search-suggestions'),
    
    # =============== JOBS - EMPLOYER ===============
    path('employer/jobs/', views.EmployerJobListView.as_view(), name='employer-jobs'),
    path('employer/jobs/<int:id>/', views.EmployerJobDetailView.as_view(), name='employer-job-detail'),
    path('employer/jobs/<int:job_id>/status/', views.update_job_status, name='update-job-status'),
    
    # =============== JOB APPLICATIONS ===============
    path('applications/', views.JobApplicationListView.as_view(), name='job-applications'),
    path('applications/<int:id>/', views.JobApplicationDetailView.as_view(), name='job-application-detail'),
    path('applications/<int:application_id>/status/', views.update_application_status, name='update-application-status'),
    path('applications/<int:application_id>/withdraw/', views.withdraw_application, name='withdraw-application'),
    
    # =============== SAVED JOBS ===============
    path('saved-jobs/', views.SavedJobListView.as_view(), name='saved-jobs'),
    path('jobs/<int:job_id>/save/', views.toggle_save_job, name='toggle-save-job'),
    
    # =============== JOB ALERTS ===============
    path('job-alerts/', views.JobAlertListView.as_view(), name='job-alerts'),
    path('job-alerts/<int:id>/', views.JobAlertDetailView.as_view(), name='job-alert-detail'),
    
    # =============== RECOMMENDATIONS ===============
    path('recommendations/', views.get_recommended_jobs, name='job-recommendations'),
    
    # =============== ADMIN ===============
    path('admin/dashboard/', views.admin_dashboard_stats, name='admin-dashboard'),
    path('admin/jobs/<int:job_id>/moderate/', views.admin_moderate_job, name='admin-moderate-job'),
    path('admin/employers/<int:employer_id>/verify/', views.admin_verify_employer, name='admin-verify-employer'),
]