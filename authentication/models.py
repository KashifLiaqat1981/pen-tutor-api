# authetication/model.py

from django.db import models, transaction, IntegrityError
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.conf import settings

class User(AbstractUser):
    USER_ROLES = [
        ('user','User'),
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
        ('subadmin', 'SubAdmin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=USER_ROLES, default='user')
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    class Meta:
        db_table = 'users'


class StudentProfile(models.Model):

    # Base Information
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    email = models.EmailField(editable=False)
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    location = models.URLField(max_length=500, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)

    # Academic Info/Preferences
    learning_mode = models.CharField(max_length=50, help_text="Home/Online",
                                     choices=[('home', 'Home'), ('online', 'Online')], blank=True)
    curriculum = models.CharField(max_length=50, help_text="Curriculum i.e. Edexcel", null=True)
    current_class = models.CharField(max_length=50, help_text="Current class/grade i.e. 1, 9, P-1", null=True)
    subjects = models.JSONField(default=list, help_text="Subjects of interest", blank=True, null=True)
    special_requirements = models.TextField(blank=True, null=True, help_text="Any special requirements or requests")
    preferred_learning_time = models.JSONField(default=list, blank=True, null=True)
    language_preferences = models.JSONField(default=list, blank=True, null=True)
    tutor_gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('any', 'Any')],
                                    blank=True, null=True)

    student_id = models.CharField(max_length=100, unique=True, blank=True, null=True) # auto generated
    is_active = models.BooleanField(default=True)


    # Course Related
    enrolled_courses = models.ManyToManyField('courses.Course', through='courses.Enrollment', related_name='enrolled_students')
    completed_courses_count = models.PositiveIntegerField(default=0)
    current_courses_count = models.PositiveIntegerField(default=0)
    attendance_percentage = models.FloatField(default=0.0)
    completed_assignments = models.PositiveIntegerField(default=0)
    certificates = models.JSONField(default=list, blank=True)
    average_course_rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Student: {self.user.email}"

    def save(self, *args, **kwargs):
        if self.user:
            self.email = self.user.email
            self.full_name = f"{self.user.first_name} {self.user.last_name}".strip()

        if not self.student_id:
            for _ in range(5):
                try:
                    with transaction.atomic():
                        last = StudentProfile.objects.select_for_update().exclude(student_id__isnull=True).order_by('-created_at').first()
                        next_num = 1 if not last else int(last.student_id.split('-')[1]) + 1
                        self.student_id = f"STU-{next_num:04d}"
                        break
                except IntegrityError:
                    continue
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['curriculum']),
            models.Index(fields=['tutor_gender']),
        ]


    # Old Fields...
    EDUCATION_LEVELS = [
        ('high_school', 'High School'),
        ('bachelors', "Bachelor's Degree"),
        ('masters', "Master's Degree"),
        ('phd', 'PhD'),
        ('other', 'Other')
    ] # not used

    EMPLOYMENT_STATUS = [
        ('student', 'Full-time Student'),
        ('employed', 'Employed'),
        ('self_employed', 'Self Employed'),
        ('unemployed', 'Looking for Opportunities'),
        ('other', 'Other')

    ] # not used
    level = models.CharField(max_length=50, help_text="Level i.e. O-level, grade", blank=True, null=True) # not needed
    field_of_study = models.CharField(max_length=200, blank=True) # not used
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVELS, blank=True) # not used
    notification_preferences = models.JSONField(default=dict, blank=True) # not needed
    age = models.PositiveIntegerField(null=True, blank=True) # not needed
    bio = models.TextField(max_length=500, blank=True) # not needed
    institution = models.CharField(max_length=200, blank=True) # not needed
    enrollment_number = models.CharField(max_length=100, blank=True, null=True) # not needed
    graduation_year = models.PositiveIntegerField(null=True, blank=True) # not needed
    gpa = models.FloatField(blank=True, null=True) # not needed
    skills = models.JSONField(default=list, blank=True) # not needed
    interests = models.JSONField(default=list, blank=True) # not needed
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, blank=True) # not needed
    current_job_title = models.CharField(max_length=200, blank=True) # not needed
    company = models.CharField(max_length=200, blank=True) # not needed
    career_goals = models.TextField(blank=True) # not needed
    linkedin_profile = models.URLField(blank=True) # not needed
    github_profile = models.URLField(blank=True) # not needed
    portfolio_website = models.URLField(blank=True) # not needed
    social_links = models.JSONField(default=dict, blank=True) # not needed


class TeacherProfile(models.Model):
    EXPERTISE_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
        ('master', 'Master')
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]

    # Base Information
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_profile')
    email = models.EmailField(editable=False)
    full_name = models.CharField(max_length=100, editable=False)
    phone = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    city = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True, null=True)

    profile_picture = models.ImageField(upload_to='teacher_profiles/', null=True, blank=True)
    resume = models.FileField(upload_to='teacher_documents/resumes/', null=True, blank=True)
    degree_certificates = models.FileField(upload_to='teacher_documents/degrees/', null=True, blank=True)
    id_proof = models.FileField(upload_to='teacher_documents/id_proofs/', null=True, blank=True)

    employee_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    headline = models.CharField(max_length=200, null=True, blank=True)
    expertise_level = models.CharField(max_length=20, choices=EXPERTISE_LEVELS,default='expert', blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(default=0, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    teaching_style = models.TextField(blank=True, null=True)
    languages_spoken = models.JSONField(default=list, blank=True, null=True)

    education = models.JSONField(default=list, blank=True, null=True)
    certifications = models.JSONField(default=list, blank=True, null=True)
    awards = models.JSONField(default=list, blank=True, null=True)
    publications = models.JSONField(default=list, blank=True, null=True)

    # Professional Links
    youtube_channel = models.URLField(blank=True, null=True)
    social_links = models.JSONField(default=dict, blank=True, null=True)
    # Availability and Preferences
    availability_schedule = models.JSONField(default=dict, blank=True, null=True)
    preferred_teaching_methods = models.JSONField(default=list, blank=True, null=True)

    # Course Related
    courses_created = models.ManyToManyField('courses.Course', related_name='instructors',blank=True)
    total_courses = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    # Status and Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Statistics
    total_course_hours = models.PositiveIntegerField(default=0)
    total_students_helped = models.PositiveIntegerField(default=0)
    response_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    average_response_time = models.DurationField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Teacher: {self.user.email}"

    def save(self, *args, **kwargs):
        if self.user:
            self.email = self.user.email
            self.full_name = f"{self.user.first_name} {self.user.last_name}".strip()

        if not self.employee_id:
            for _ in range(5):
                try:
                    with transaction.atomic():
                        last = TeacherProfile.objects.select_for_update().exclude(employee_id__isnull=True).order_by('-created_at').first()
                        next_num = 1 if not last else int(last.employee_id.split('-')[1]) + 1
                        self.employee_id = f"TEA-{next_num:04d}"
                        break
                except IntegrityError:
                    continue
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['expertise_level', 'years_of_experience']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['status']),
        ]

    # old fields
    EMPLOYMENT_TYPE = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('freelance', 'Freelance')
    ]
    age = models.PositiveIntegerField(null=True, blank=True) # not needed
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE,default='part_time', blank=True, null=True) # not needed
    course_categories = models.JSONField(default=list, blank=True, null=True) # not needed
    bio = models.TextField(blank=True, null=True) # not needed
    expertise_areas = models.JSONField(default=list, blank=True, null=True) # not needed
    notification_preferences = models.JSONField(default=dict, blank=True, null=True) # not needed
    linkedin_profile = models.URLField(blank=True, null=True) # not needed
    github_profile = models.URLField(blank=True, null=True) # not needed
    personal_website = models.URLField(blank=True, null=True) # not needed


class StudentQuery(models.Model):
    """
    Student Query Form - for visitors who want to inquire before registration
    """
    # Basic Info
    name = models.CharField(max_length=100)
    email = models.EmailField()
    contact_no = models.CharField(max_length=15)
    tutor_gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('any', 'Any')],
                                    blank=True)
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    area = models.CharField(max_length=100, blank=True, null=True)
    location = models.URLField(max_length=500, blank=True, null=True)

    # Academic Info
    curriculum = models.CharField(max_length=50, help_text="Curriculum i.e. Edexcel")
    learning_mode = models.CharField(max_length=50, help_text="Home/Online", choices=[('home', 'Home'), ('online', 'Online')],
                                     blank=True)


    current_class = models.CharField(max_length=50, help_text="Current class/grade i.e. 1, 9, P-1")
    subjects = models.JSONField(default=list, help_text="Subjects of interest", blank=True)
    special_requirements = models.TextField(blank=True, null=True, help_text="Any special requirements or requests")

    # Status
    is_registered = models.BooleanField(default=False, help_text="Has this person registered as a student?")
    is_processed = models.BooleanField(default=False, help_text="Has admin processed this query?")
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes for this query")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Link to user if they register later
    linked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User account if they registered later"
    )

    def __str__(self):
        return f"Query by {self.name} - {self.email}"

    class Meta:
        db_table = 'student_queries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_registered']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['created_at']),
        ]


    level = models.CharField(max_length=50, help_text="Level i.e. O-level, grade", blank=True, null=True) # not needed

