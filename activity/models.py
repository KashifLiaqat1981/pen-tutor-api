# activity/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    email = models.EmailField(null=True, blank=True)
    action = models.CharField(max_length=255)  # e.g., "Created Assignment"
    module = models.CharField(max_length=100)  # e.g., "Assignments"
    page_url = models.URLField(max_length=500, null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    extra_info = models.JSONField(null=True, blank=True)  # Store additional details

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} ({self.module})"
