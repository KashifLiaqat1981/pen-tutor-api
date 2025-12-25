# payment/models.py - Updated to link with courses

from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()

class Payment(models.Model):
    GATEWAY_CHOICES = (
        ('jazzcash', 'JazzCash'),
        ('easypaisa', 'EasyPaisa'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments',null=True, blank=True)
    group_session = models.ForeignKey(
        'group_sessions.GroupSession',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    txn_ref = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                        models.Q(course__isnull=False, group_session__isnull=True) |
                        models.Q(course__isnull=True, group_session__isnull=False) |
                        models.Q(course__isnull=True, group_session__isnull=True)
                ),
                name='only_one_content_type'
            )
        ]

    def __str__(self):
        if self.course:
            return f"{self.user.username} - Course: {self.course.title} - {self.amount}"
        if self.group_session:
            return f"{self.user.username} - Group Session: {self.group_session.title} - {self.amount}"
        return f"{self.user.username} - Payment {self.txn_ref}"