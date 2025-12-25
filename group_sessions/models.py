# group_sessions/models.py
from django.db import models
from django.db.models import Sum
from django.contrib.auth import get_user_model
import uuid
from django.utils import timezone
from datetime import timedelta
from payments.models import Payment

User = get_user_model()


class GroupSession(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_sessions')
    title = models.CharField(max_length=200)
    description = models.TextField()
    short_description = models.TextField(max_length=300)

    # Session Details
    subject = models.JSONField(default=list, blank=True, null=True)  # e.g., "Math", "Programming", "Art"
    tags = models.JSONField(default=list, blank=True)  # ["python", "data-science", "beginners"]

    # Schedule
    starting_date = models.DateField(blank=True, null=True)
    days = models.JSONField(default=list, blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    class_duration = models.IntegerField(default=60)
    session_duration = models.IntegerField(default=1, help_text="duration of session in months")

    # Capacity & Pricing
    max_students = models.IntegerField(default=20)
    min_students = models.IntegerField(default=5)
    current_enrollments = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default='USD')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_free = models.BooleanField(default=False)

    # Meeting Link
    meeting = models.OneToOneField("meetings.Meeting", on_delete=models.SET_NULL, null=True, blank=True, related_name='group_session_instance')

    # Status & Visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['teacher', 'status']),
        ]

    @property
    def is_live(self):
        now = timezone.now()
        return self.status == 'published' and self.start_time <= now <= self.end_time

    @property
    def is_completed(self):
        return self.end_time and timezone.now() > self.end_time

    def save(self, *args, **kwargs):
        if self.start_time and not self.end_time:
            self.end_time = self.start_time + timedelta(minutes=self.class_duration)

        super().save(*args, **kwargs)

    def create_meeting_instance(self):
        if self.meeting:
            return  # Already exists

        from meetings.models import Meeting

        meeting = Meeting.objects.create(
            host=self.teacher,
            title=self.title,
            meeting_type='scheduled',
            access_type='private',
            scheduled_time=self.start_time,
            max_participants=self.max_students,
            is_password_required=True,
            course=None,
        )
        self.meeting = meeting
        super(GroupSession, self).save(update_fields=['meeting'])

    @property
    def is_upcoming(self):
        return self.status == 'published' and timezone.now() < self.start_time

    @property
    def is_available(self):
        now = timezone.now()
        return (
                self.status == 'published' and
                self.current_enrollments < self.max_students and
                (not self.end_time or now <= self.end_time)
        )

    @property
    def seats_remaining(self):
        return self.max_students - self.current_enrollments

    def can_student_join(self, student):
        """Check if a student can join this session"""
        # Check enrollment
        if GroupSessionEnrollment.objects.filter(
                session=self,
                student=student,
                status='enrolled'
        ).exists():
            return True, "Already enrolled"

        # Check capacity
        if self.current_enrollments >= self.max_students:
            return False, "Session is full"

        # Check time
        now = timezone.now()

        if self.end_time and now > self.end_time:
            return False, "Session has ended"

        # Check payment for paid sessions
        if not self.is_free:
            has_payment = Payment.objects.filter(
                user=student,
                group_session=self,
                is_successful=True,
            ).exists()
            if not has_payment:
                return False, "Payment required"

        return True, "Can enroll"

    def __str__(self):
        return f"{self.title} by {self.teacher.username}"


class GroupSessionEnrollment(models.Model):
    ENROLLMENT_STATUS = [
        ('pending', 'Pending'),
        ('enrolled', 'Enrolled'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(GroupSession, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_session_enrollments')

    # Status
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS, default='pending')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Payment Reference
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)

    # Attendance
    attended = models.BooleanField(default=False)
    attendance_duration = models.IntegerField(default=0)  # in minutes

    # Feedback
    rating = models.IntegerField(null=True, blank=True)  # 1-5
    review = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['session', 'student']
        ordering = ['-enrolled_at']


    def update_enrollment_count(self):
        """Recalculate current_enrollments based on actual enrolled students"""
        self.current_enrollments = self.enrollments.filter(status='enrolled').count()
        self.save(update_fields=['current_enrollments'])


    def mark_attended(self, duration_minutes=0):
        self.attended = True
        self.attendance_duration = duration_minutes
        self.completed_at = timezone.now()
        self.save()

    @property
    def can_join_meeting(self):
        """Check if student can join the meeting"""
        if not self.session.meeting:
            return False

        # Check enrollment status
        if self.status != 'enrolled':
            return False

        # Check if session is live or about to start (15 mins before)
        now = timezone.now()
        start_time = self.session.start_time
        end_time = self.session.end_time

        # Allow joining 15 minutes before start until end
        can_join_time = (start_time - timedelta(minutes=15)) <= now <= end_time

        return can_join_time and self.session.status == 'published'

    @property
    def total_attendance_duration(self):
        """Total minutes attended across all join/leave events"""
        total = self.attendance_logs.aggregate(
            total=Sum('duration_minutes')
        )['total']
        return total or 0

    @property
    def join_count(self):
        """How many times the student joined"""
        return self.attendance_logs.count()

    @property
    def attended_sessions(self):
        """Number of times they stayed > X minutes (e.g., 5 min)"""
        return self.attendance_logs.filter(duration_minutes__gte=5).count()


class AttendanceLog(models.Model):
    enrollment = models.ForeignKey(
        GroupSessionEnrollment,
        on_delete=models.CASCADE,
        related_name='attendance_logs'
    )
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)  # Calculated when left

    class Meta:
        ordering = ['joined_at']
        indexes = [
            models.Index(fields=['enrollment', 'joined_at']),
        ]

    def __str__(self):
        return f"{self.enrollment.student} - Joined {self.joined_at}"

    def mark_left(self):
        """Call this when student leaves"""
        if not self.left_at:
            self.left_at = timezone.now()
            delta = self.left_at - self.joined_at
            self.duration_minutes = int(delta.total_seconds() // 60)
            self.save()