# group_sessions/signals.py

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import GroupSessionEnrollment

@receiver(pre_save, sender=GroupSessionEnrollment)
def capture_old_status(sender, instance, **kwargs):
    """
    Capture the old status before saving (for updates)
    """
    if instance.pk:
        try:
            instance._old_status = GroupSessionEnrollment.objects.get(pk=instance.pk).status
        except GroupSessionEnrollment.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None  # New object


@receiver(post_save, sender=GroupSessionEnrollment)
def update_session_enrollment_count(sender, instance, created, **kwargs):
    """
    Update GroupSession.current_enrollments when enrollment is created or status changes
    """
    session = instance.session
    old_status = getattr(instance, '_old_status', None)

    if created:
        # New enrollment
        if instance.status == 'enrolled':
            session.current_enrollments += 1
            session.save(update_fields=['current_enrollments'])
    else:
        # Existing enrollment updated
        if old_status != instance.status:
            if instance.status == 'enrolled' and old_status != 'enrolled':
                session.current_enrollments += 1
            elif old_status == 'enrolled' and instance.status != 'enrolled':
                session.current_enrollments -= 1
            session.save(update_fields=['current_enrollments'])


@receiver(post_delete, sender=GroupSessionEnrollment)
def decrease_enrollment_count_on_delete(sender, instance, **kwargs):
    """
    Decrease count if a enrolled student is deleted
    """
    if instance.status == 'enrolled':
        session = instance.session
        session.current_enrollments = max(0, session.current_enrollments - 1)
        session.save(update_fields=['current_enrollments'])