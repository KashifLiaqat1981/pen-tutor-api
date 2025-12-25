# authentication/signals.py

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StudentQuery
from django.utils import timezone
from job_board.models import JobPost


@receiver(post_save, sender=StudentQuery)
def handle_query_status_change(sender, instance, created, **kwargs):
    if created:
        return

    if instance.status == 'approved' and not instance.linked_job:
        # VERY IMPORTANT: defer execution until admin transaction commits
        transaction.on_commit(
            lambda: create_job_from_query(instance.pk)
        )

def create_job_from_query(query_id):
    try:
        query = StudentQuery.objects.select_related(
            'linked_user__student_profile'
        ).get(pk=query_id)

        # Safety re-check
        if query.status != 'approved' or query.linked_job:
            return None

        if not query.linked_user or not hasattr(query.linked_user, 'student_profile'):
            StudentQuery.objects.filter(pk=query.pk).update(
                admin_notes="Approved – waiting for student registration"
            )
            return None

        student_profile = query.linked_user.student_profile

        job_post = JobPost.objects.create(
            student=student_profile,
            title=f"Tutoring request for {query.curriculum} - {query.current_class}",
            description=(
                f"Curriculum: {query.curriculum or 'Not specified'}\n"
                f"Class: {query.current_class or 'Not specified'}\n"
                f"Requirements: {query.special_requirements or 'None'}"
            ),
            curriculum=query.curriculum,
            current_class=query.current_class,
            subject=query.subjects if query.subjects else "General Tutoring",
            teaching_mode=(
                'home' if query.learning_mode == 'home'
                else 'online' if query.learning_mode == 'online'
                else 'hybrid'
            ),
            budget_amount=15.00,
            budget_type='per_hour',
            location=query.location or query.address or f"{query.city}, {query.country}",
            gender=query.tutor_gender if query.tutor_gender in ['male', 'female', 'any'] else 'any',
            status='open',
            deadline=timezone.now() + timezone.timedelta(days=7),
            additional_notes=f"Converted from student query {query.query_id}",
        )

        StudentQuery.objects.filter(pk=query.pk).update(
            linked_job=job_post
        )

        return job_post

    except Exception as e:
        print(f"[Query→Job Error] {e}")
        return None