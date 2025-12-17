# authetication/model.py

from django.db import models, transaction, IntegrityError
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.conf import settings

def generate_student_id():
    return f"PTS-{uuid.uuid4().hex[:8].upper()}"

def generate_teacher_id():
    return f"PT-{uuid.uuid4().hex[:8].upper()}"

def generate_query_id():
    return f"PTQ-{uuid.uuid4().hex[:8].upper()}"

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
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    location = models.URLField(max_length=500, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)

    # Academic Info/Preferences
    learning_mode = models.CharField(max_length=50, help_text="Home/Online or both",
                                     choices=[('home', 'Home'), ('online', 'Online'), ('both', 'Both')], blank=True, null=True)
    curriculum = models.CharField(max_length=50, help_text="Curriculum i.e. Edexcel", blank=True, null=True)
    current_class = models.CharField(max_length=50, help_text="Current class/grade i.e. 1, 9, P-1", blank=True, null=True)
    subjects = models.JSONField(default=list, help_text="Subjects of interest", blank=True, null=True)
    special_requirements = models.TextField(blank=True, null=True, help_text="Any special requirements or requests")
    preferred_learning_time = models.JSONField(default=list, blank=True, null=True)
    language_preferences = models.JSONField(default=list, blank=True, null=True)
    tutor_gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('any', 'Any')],
                                    blank=True, null=True)

    student_id = models.CharField(max_length=20, unique=True, editable=False,
                                default=generate_student_id)
    is_active = models.BooleanField(default=True)


    # Course Related
    enrolled_courses = models.ManyToManyField('courses.Course', through='courses.Enrollment', related_name='enrolled_students')
    completed_courses_count = models.PositiveIntegerField(default=0)
    current_courses_count = models.PositiveIntegerField(default=0)
    attendance_percentage = models.FloatField(default=0.0)
    completed_assignments = models.PositiveIntegerField(default=0)
    certificates = models.JSONField(default=list, blank=True, null=True)
    average_course_rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Student_id: {self.student_id} {self.user.email}"

    def save(self, *args, **kwargs):
        if self.user and not self.pk:
            self.email = self.user.email
            if not self.full_name:
                self.full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['curriculum']),
            models.Index(fields=['tutor_gender']),
        ]


class TeacherProfile(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]

    # Base Information
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_profile')
    email = models.EmailField(editable=False)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    location = models.URLField(max_length=500, blank=True, null=True)
    identity_no = models.CharField(max_length=50, blank=True, help_text="Enter CNIC or Passport number", null=True)

    teaching_mode = models.CharField(max_length=50, help_text="Home/Online or both",
                                     choices=[('home', 'Home'), ('online', 'Online'), ('both', 'Both')], blank=True, null=True)
    subjects = models.JSONField(default=list, help_text="Subjects you can teach", blank=True, null=True)
    curriculum = models.JSONField(default=list, help_text="Curriculum i.e. Edexcel you can teach", blank=True, null=True)
    classes = models.JSONField(default=list, help_text="Class/grade i.e. 1, 9, P-1 you can teach", blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(default=0, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    headline = models.CharField(max_length=200, null=True, blank=True)

    profile_picture = models.ImageField(upload_to='teacher_profiles/', null=True, blank=True)
    resume = models.FileField(upload_to='teacher_documents/resumes/', null=True, blank=True)
    degree_certificates = models.FileField(upload_to='teacher_documents/degrees/', null=True, blank=True)
    id_proof = models.FileField(upload_to='teacher_documents/id_proofs/', null=True, blank=True)

    teacher_id = models.CharField(max_length=20, unique=True, editable=False,
                                default=generate_teacher_id)

    department = models.CharField(max_length=100, blank=True, null=True)
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
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_profile_complete(self):
        """
        Returns True if all required fields for a complete teacher profile are filled.
        Adjust the list below based on what YOU consider "complete".
        """
        required_fields = [
            'full_name', 'phone', 'date_of_birth', 'gender', 'country', 'city', 'address', 'identity_no',
            'teaching_mode', 'subjects', 'curriculum', 'classes', 'years_of_experience', 'hourly_rate',
            'headline', 'profile_picture', 'resume', 'degree_certificates', 'id_proof', 'location'
        ]

        for field_name in required_fields:
            value = getattr(self, field_name)
            if value in (None, '', [], {}):  # handles None, empty string, empty list/dict
                return False

        return True

    @property
    def profile_completion_percentage(self):
        """
        Bonus: Returns a percentage (0-100) of profile completeness.
        Great for progress bars in frontend!
        """
        if not hasattr(self, '_completion_fields'):
            self._completion_fields = [
                'full_name', 'phone', 'date_of_birth', 'gender', 'country', 'city',
                'address', 'identity_no', 'teaching_mode', 'subjects', 'curriculum',
                'classes', 'years_of_experience', 'hourly_rate', 'headline',
                'profile_picture', 'resume', 'degree_certificates', 'id_proof'
            ]

        total = len(self._completion_fields)
        filled = sum(1 for field in self._completion_fields if getattr(self, field) not in (None, '', [], {}))

        return round((filled / total) * 100) if total > 0 else 0

    def __str__(self):
        return f"Teacher_id: {self.teacher_id} {self.user.email}"

    def save(self, *args, **kwargs):
        if self.user and not self.pk:
            self.email = self.user.email
            if not self.full_name:
                self.full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['years_of_experience']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['status']),
        ]


class StudentQuery(models.Model):
    """
    Student Query Form - for visitors who want to inquire before registration
    """
    # Basic Info
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    tutor_gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('any', 'Any')],
                                    blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    location = models.URLField(max_length=500, blank=True, null=True)

    # Academic Info
    curriculum = models.CharField(max_length=50, help_text="Curriculum i.e. Edexcel", blank=True, null=True)
    learning_mode = models.CharField(max_length=50, help_text="Home/Online or both",
                                     choices=[('home', 'Home'), ('online', 'Online'), ('both', 'Both')], blank=True, null=True)

    current_class = models.CharField(max_length=50, help_text="Current class/grade i.e. 1, 9, P-1", blank=True, null=True)
    subjects = models.JSONField(default=list, help_text="Subjects of interest", blank=True, null=True)
    special_requirements = models.TextField(blank=True, null=True, help_text="Any special requirements or requests")

    # Status
    query_id = models.CharField(max_length=20, unique=True, editable=False,
        default=generate_query_id)
    is_registered = models.BooleanField(default=False, help_text="Has this person registered as a student?")
    is_processed = models.BooleanField(default=False, help_text="Has admin processed this query?")
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes for this query")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True)
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
        return f"Query_id {self.query_id} by {self.full_name} - {self.email}"

    class Meta:
        db_table = 'student_queries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_registered']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['created_at']),
        ]
