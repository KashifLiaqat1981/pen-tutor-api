# # authentication/signals.py
#
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import User
# from .models import TeacherProfile, StudentProfile
#
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if not created:
#         return
#
#     if instance.role == 'teacher':
#         TeacherProfile.objects.create(
#             user=instance,
#             email=instance.email,
#             full_name=instance.get_full_name()
#         )
#
#     elif instance.role == 'student':
#         StudentProfile.objects.create(
#             user=instance,
#             email=instance.email,
#             full_name=instance.get_full_name()
#         )
#
#
# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     if instance.role == 'teacher' and hasattr(instance, 'teacher_profile'):
#         instance.teacher_profile.save()
#
#     elif instance.role == 'student' and hasattr(instance, 'student_profile'):
#         instance.student_profile.save()
