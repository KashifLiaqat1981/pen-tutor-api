# job_board/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from authentication.models import StudentProfile, TeacherProfile

User = settings.AUTH_USER_MODEL

class JobPost(models.Model):
    TEACHING_MODE_CHOICES = [
        ('online', 'Online'),
        ('home', 'Home'),
        ('hybrid', 'Hybrid')
    ]

    BUDGET_TYPE_CHOICES = [
        ('per_hour', 'Per Hour'),
        ('per_day', 'Per Day'),
        ('total', 'Total Amount'),
        ('fixed', 'Fixed'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('any', 'Any'),
    ]

    DAYS_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    # Core fields
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='job_posts')
    title = models.CharField(max_length=200)
    description = models.TextField()
    curriculum = models.CharField(max_length=30, blank=True, null=True)
    current_class = models.CharField(max_length=30, blank=True, null=True)

    subject = models.JSONField(default=list, help_text="Subjects you can teach", blank=True, null=True)
    
    # Teaching preferences
    teaching_mode = models.CharField(max_length=10, choices=TEACHING_MODE_CHOICES, default='hybrid')
    
    # Budget information
    budget_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    budget_type = models.CharField(max_length=10, choices=BUDGET_TYPE_CHOICES, default='per_hour')

    # Additional information
    additional_notes = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True,
        help_text="Required for physical teaching mode")

    # Preferred time to study (e.g., 5:00 PM)
    time_to_study_start = models.TimeField(null=True, blank=True, help_text="Preferred study time")
    time_to_study_end = models.TimeField(null=True, blank=True, help_text="Preferred study time")

    # Preferred days to study (multiple days)
    days_to_study = models.JSONField(default=list, help_text="Days available for class", blank=True, null=True)

    # Preferred teacher gender
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='any')
    
    # Status and management
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    selected_teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_jobs'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(null=True, blank=True, help_text="When do you need this to be completed?")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['student', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.student.user.username}"

    
    @property
    def applications_count(self):
        """Return number of applications for this job"""
        return self.applications.count()
    
    @property
    def is_open(self):
        """Check if job is still accepting applications"""
        return self.status == 'open'


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    # Core relationships
    job_post = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    
    # Application content
    chat_room = models.ForeignKey(
        'chate_box.ChatRoom',  # Note: Use string reference since it's in another app
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_applications'
    )

    teacher_finalized_days = models.JSONField(default=list, blank=True, null=True)
    teacher_finalized_time_start = models.TimeField(null=True, blank=True)
    teacher_finalized_time_end = models.TimeField(null=True, blank=True)
    teacher_finalized_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    teacher_demo_class_time = models.DateTimeField(null=True, blank=True)
    teacher_finalized = models.BooleanField(default=False)

    student_finalized_days = models.JSONField(default=list, blank=True, null=True)
    student_finalized_time_start = models.TimeField(null=True, blank=True)
    student_finalized_time_end = models.TimeField(null=True, blank=True)
    student_finalized_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    student_demo_class_time = models.DateTimeField(null=True, blank=True)
    student_finalized = models.BooleanField(default=False)

    # Also add these fields for finalization
    finalized_days = models.JSONField(default=list, blank=True, null=True)
    finalized_time_start = models.TimeField(null=True, blank=True)
    finalized_time_end = models.TimeField(null=True, blank=True)
    finalized_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    demo_class_time = models.DateTimeField(null=True, blank=True)
    is_finalized = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job_post', 'teacher']  # Prevent duplicate applications
        indexes = [
            models.Index(fields=['job_post', 'status']),
            models.Index(fields=['teacher', 'status']),
        ]
    
    def __str__(self):
        return f"{self.teacher.user.username} -> {self.job_post.title}"
    
    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def both_finalized(self):
        return self.teacher_finalized and self.student_finalized

    @property
    def is_accepted(self):
        return self.status == 'accepted'


# Optional: Job Review model for after completion
class JobReview(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    job_post = models.OneToOneField(
        JobPost,
        on_delete=models.CASCADE,
        related_name='review'
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_reviews'
    )
    reviewed = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_reviews'
    )
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.rating} stars from {self.reviewer.username} to {self.reviewed.username}"