# live_classes/views.py

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from rest_framework.exceptions import ValidationError

from .models import (
    LiveClassSchedule, LiveClassSubscription, LiveClassSession,
    LiveClassInvitation, ClassReschedule, LiveClassPayment
)
import uuid
from .serializers import (
    LiveClassScheduleSerializer, LiveClassScheduleCreateSerializer,
    LiveClassSubscriptionSerializer, LiveClassSessionSerializer,
    ClassRescheduleSerializer, RescheduleRequestSerializer,
    LiveClassPaymentSerializer, SubscriptionCreateSerializer,
    TeacherScheduleListSerializer, StudentScheduleListSerializer, MeetingRescheduleSerializer,
    LiveClassInvitationSerializer, InvitationRespondSerializer, PortalLiveClassSessionSerializer
)
from authentication.models import StudentProfile, TeacherProfile,User
from meetings.models import Meeting
from notifications.models import Notification
from rest_framework.permissions import IsAuthenticated
from job_board.models import JobApplication
from django.db.models import Q


def _student_is_available(student_profile, candidate_dt, duration_minutes):
    """Basic overlap check against existing live class sessions for the student."""
    start = candidate_dt
    end = candidate_dt + timedelta(minutes=duration_minutes)

    existing = LiveClassSession.objects.filter(
        schedule__student=student_profile,
        status__in=['scheduled', 'ongoing', 'rescheduled'],
        scheduled_datetime__lt=end,
        scheduled_datetime__gt=start - timedelta(minutes=duration_minutes)
    ).select_related('schedule')

    for session in existing:
        s_start = session.scheduled_datetime
        s_end = session.scheduled_datetime + timedelta(minutes=session.duration)
        if start < s_end and end > s_start:
            return False
    return True


def _validate_student_availability_for_schedule(student_profile, class_days, class_times, start_date, end_date, duration_minutes):
    """Validate availability for the first few occurrences of the weekly schedule."""
    probe_start = start_date
    probe_end = min(end_date, start_date + timedelta(days=14)) if end_date else (start_date + timedelta(days=14))
    cursor = probe_start
    while cursor <= probe_end:
        day_key = cursor.strftime('%A').lower()
        if day_key in class_days:
            time_str = class_times.get(day_key)
            if time_str:
                naive_dt = datetime.combine(cursor, datetime.strptime(time_str, '%H:%M').time())
                candidate = timezone.make_aware(naive_dt) if timezone.is_naive(naive_dt) else naive_dt
                if not _student_is_available(student_profile, candidate, duration_minutes):
                    raise ValidationError({
                        'detail': f"Student is not available at {candidate.strftime('%Y-%m-%d %H:%M')}"
                    })
        cursor += timedelta(days=1)


# Teacher Views
class TeacherScheduleListView(generics.ListAPIView):
    """List all schedules created by a teacher"""
    serializer_class = TeacherScheduleListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        teacher_profile = get_object_or_404(TeacherProfile, user=self.request.user)
        return LiveClassSchedule.objects.filter(teacher=teacher_profile)
    def get_serializer_context(self):
        """Pass request to serializer for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CreateLiveClassScheduleView(generics.CreateAPIView):
    """Teacher creates a live class schedule for a student"""
    serializer_class = LiveClassScheduleCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        teacher_profile = get_object_or_404(TeacherProfile, user=self.request.user)
        student_obj = serializer.validated_data["student"]

        if not student_obj or not hasattr(student_obj, 'user'):
            raise ValidationError({"student": "Invalid student profile"})

        existing_schedule = LiveClassSchedule.objects.filter(
            teacher=teacher_profile,
            student=student_obj,
            subject=serializer.validated_data['subject']
        ).first()
        if existing_schedule:
            raise ValidationError({"detail": "A schedule already exists for this teacher, student, and subject."})

        _validate_student_availability_for_schedule(
            student_profile=student_obj,
            class_days=serializer.validated_data['class_days'],
            class_times=serializer.validated_data['class_times'],
            start_date=serializer.validated_data['start_date'],
            end_date=serializer.validated_data.get('end_date'),
            duration_minutes=serializer.validated_data.get('class_duration') or 60,
        )

        with transaction.atomic():
            schedule = serializer.save(teacher=teacher_profile)

            next_class = schedule.get_next_class_date()
            if next_class and timezone.is_naive(next_class):
                next_class = timezone.make_aware(next_class)

            invitation = LiveClassInvitation.objects.create(
                schedule=schedule,
                teacher=teacher_profile,
                student=student_obj,
                first_class_datetime=next_class,
                budget=schedule.weekly_payment,
                is_demo_free=True,
            )

            Notification.objects.create(
                recipient=student_obj.user,
                sender=self.request.user,
                notification_type='live_class_scheduled',
                title='Individual Live Class Invitation',
                message=(
                    f"Teacher ID: {teacher_profile.id}. "
                    f"Date/Time: {(next_class.strftime('%Y-%m-%d %H:%M') if next_class else 'TBD')}. "
                    f"Budget: {invitation.budget}. "
                    f"Demo class is FREE; after demo, paid classes start."
                )
            )

            admin_user = User.objects.filter(role='admin').first()
            if admin_user:
                Notification.objects.create(
                    recipient=admin_user,
                    sender=self.request.user,
                    notification_type='general',
                    title='New Individual Live Class Invitation',
                    message=(
                        f"Teacher: {teacher_profile.full_name} (ID: {teacher_profile.id}) "
                        f"Student: {student_obj.full_name} (ID: {student_obj.id})"
                    )
                )

        return schedule


class UpdateLiveClassScheduleView(generics.UpdateAPIView):
    """Teacher updates their live class schedule"""
    serializer_class = LiveClassScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'schedule_id'
    
    def get_queryset(self):
        teacher_profile = get_object_or_404(TeacherProfile, user=self.request.user)
        return LiveClassSchedule.objects.filter(teacher=teacher_profile)


class RescheduleMeetingView(generics.UpdateAPIView):
    """Teacher updates (reschedules) a single meeting"""
    serializer_class = MeetingRescheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'   # Meeting ka id use karenge

    def get_queryset(self):
        # Sirf apne meetings update kar sake
        return Meeting.objects.filter(host=self.request.user)


# Student Views
class StudentScheduleListView(generics.ListAPIView):
    """List all schedules for a student"""
    serializer_class = StudentScheduleListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        student_profile = get_object_or_404(StudentProfile, user=self.request.user)
        return LiveClassSchedule.objects.filter(student=student_profile,is_active=True,status='accepted')


class StudentSubscriptionListView(generics.ListAPIView):
    """List student's subscriptions"""
    serializer_class = LiveClassSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        student_profile = get_object_or_404(StudentProfile, user=self.request.user)
        return LiveClassSubscription.objects.filter(student=student_profile)


class CreateSubscriptionView(generics.CreateAPIView):
    """Student creates a subscription for live classes"""
    serializer_class = SubscriptionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        student_profile = get_object_or_404(StudentProfile, user=self.request.user)
        subscription = serializer.save(student=student_profile)
        
        # Create payment record
        payment = LiveClassPayment.objects.create(
            subscription=subscription,
            student=student_profile,
            schedule=subscription.schedule,
            amount=subscription.amount_paid,
            payment_method=subscription.payment_method,
            transaction_reference=subscription.transaction_id,
            status='completed'
        )
        payment.mark_completed()


# Session Management Views
class SessionListView(generics.ListAPIView):
    """List sessions - filtered by user role"""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if getattr(self.request.user, 'role', None) == 'admin':
            return LiveClassSessionSerializer
        return PortalLiveClassSessionSerializer
    
    def get_queryset(self):
        user = self.request.user

        if hasattr(user, 'teacher_profile'):
            return LiveClassSession.objects.filter(
                schedule__teacher=user.teacher_profile,
                schedule__invitation__status='accepted'
            ).order_by('-scheduled_datetime')
        elif hasattr(user, 'student_profile'):
            return LiveClassSession.objects.filter(
                schedule__student=user.student_profile,
                schedule__invitation__status='accepted'  
            ).order_by('-scheduled_datetime')
        else:
            return LiveClassSession.objects.none()

class StudentInvitationListView(generics.ListAPIView):
    serializer_class = LiveClassInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        student_profile = get_object_or_404(StudentProfile, user=self.request.user)
        return LiveClassInvitation.objects.filter(student=student_profile)


class TeacherInvitationListView(generics.ListAPIView):
    serializer_class = LiveClassInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        teacher_profile = get_object_or_404(TeacherProfile, user=self.request.user)
        return LiveClassInvitation.objects.filter(teacher=teacher_profile)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def respond_to_invitation(request, invitation_id):
    """Student accepts/rejects an invitation."""
    if not hasattr(request.user, 'student_profile'):
        return Response({'error': 'Only student can respond to invitation'}, status=status.HTTP_403_FORBIDDEN)

    invitation = get_object_or_404(LiveClassInvitation, invitation_id=invitation_id)
    if invitation.student != request.user.student_profile:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    serializer = InvitationRespondSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    action = serializer.validated_data['action']

    if invitation.status != 'pending':
        return Response({'error': 'Invitation already responded'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        if action == 'reject':
            invitation.status = 'rejected'
            invitation.responded_at = timezone.now()
            invitation.save(update_fields=['status', 'responded_at'])

            invitation.schedule.is_active = False
            invitation.schedule.save(update_fields=['is_active'])

            Notification.objects.create(
                recipient=invitation.teacher.user,
                sender=request.user,
                notification_type='general',
                title='Invitation Rejected',
                message=f"Student ID: {invitation.student.id} rejected your invitation for {invitation.schedule.subject}."
            )

            return Response({'status': 'rejected'})

        invitation.status = 'accepted'
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])

        demo_meeting = invitation.schedule.create_demo_class()
        if demo_meeting:
            LiveClassSession.objects.get_or_create(
                schedule=invitation.schedule,
                scheduled_datetime=demo_meeting.scheduled_time,
                defaults={
                    'meeting': demo_meeting,
                    'duration': invitation.schedule.class_duration,
                    'is_demo': True,
                }
            )

                # Create next 7 days' sessions
        from datetime import timedelta
        schedule = invitation.schedule
        today = timezone.now().date()

        for i in range(7):
            target_date = today + timedelta(days=i)
            day_name = target_date.strftime('%A').lower()
            
            if day_name in schedule.class_days:
                class_time_str = schedule.class_times.get(day_name)
                if class_time_str:
                    class_time = datetime.strptime(class_time_str, '%H:%M').time()
                    scheduled_dt = timezone.make_aware(datetime.combine(target_date, class_time))
                    
                    # Skip if already created (demo)
                    if not LiveClassSession.objects.filter(
                        schedule=schedule,
                        scheduled_datetime=scheduled_dt
                    ).exists():
                        LiveClassSession.objects.create(
                            schedule=schedule,
                            scheduled_datetime=scheduled_dt,
                            duration=schedule.class_duration,
                            is_demo=False
                        )

        Notification.objects.create(
            recipient=invitation.teacher.user,
            sender=request.user,
            notification_type='general',
            title='Invitation Accepted',
            message=f"Student ID: {invitation.student.id} accepted your invitation for {invitation.schedule.subject}."
        )

    return Response({'status': 'accepted'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_live_class(request, schedule_id):
    """Student or teacher joins a live class"""
    schedule = get_object_or_404(LiveClassSchedule, schedule_id=schedule_id)
    user = request.user
    
    # Check if invitation is accepted before allowing join
    invitation = getattr(schedule, 'invitation', None)
    if invitation and invitation.status != 'accepted':
        return Response(
            {'error': 'Invitation not yet accepted'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if user can join
    if hasattr(user, 'student_profile'):
        student = user.student_profile
        if schedule.student != student:
            return Response(
                {'error': 'You are not enrolled in this schedule'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if demo or has active subscription
        if not schedule.demo_completed:
            can_join = True
        else:
            active_sub = LiveClassSubscription.objects.filter(
                schedule=schedule,
                student=student,
                status='active'
            ).first()
            can_join = active_sub and active_sub.can_attend_class()
        
        if not can_join:
            return Response(
                {'error': 'No active subscription or demo completed'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    
    elif hasattr(user, 'teacher_profile'):
        if schedule.teacher != user.teacher_profile:
            return Response(
                {'error': 'You are not the teacher for this schedule'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'Invalid user type'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get or create current session
    now = timezone.now()
    current_session = LiveClassSession.objects.filter(
        schedule=schedule,
        scheduled_datetime__date=now.date(),
        status__in=['scheduled', 'ongoing']
    ).first()
    
    if not current_session:
        return Response(
            {'error': 'No scheduled class found for today'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Create or get meeting
    meeting = current_session.meeting
    if not meeting:
        meeting = current_session.create_meeting()
    
    # Update session status
    if current_session.status == 'scheduled':
        current_session.status = 'ongoing'
        current_session.actual_datetime = now
        current_session.save()
    
    # Track join time
    if hasattr(user, 'student_profile'):
        current_session.student_joined = True
        current_session.join_time_student = now
    elif hasattr(user, 'teacher_profile'):
        current_session.teacher_joined = True
        current_session.join_time_teacher = now
    
    current_session.save()
    
    return Response({
        'meeting_id': meeting.meeting_id,
        'meeting_password': meeting.password,
        'session_id': current_session.session_id
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def end_live_class(request, session_id):
    """Teacher ends a live class session"""
    session = get_object_or_404(LiveClassSession, session_id=session_id)
    
    # Only teacher can end class
    if not hasattr(request.user, 'teacher_profile') or session.schedule.teacher != request.user.teacher_profile:
        return Response(
            {'error': 'Only the teacher can end the class'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Mark session as completed
    session.mark_completed()
    
    # End meeting if exists
    if session.meeting:
        session.meeting.end_meeting()
    
    # Mark demo as completed if it was a demo
    if session.is_demo:
        session.schedule.demo_completed = True
        session.schedule.demo_date = timezone.now()
        session.schedule.save()
    
    return Response({'message': 'Class ended successfully'})


# Reschedule Views
class RescheduleRequestView(generics.CreateAPIView):
    """Create a reschedule request"""
    serializer_class = RescheduleRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)
        
        # Notify admin
        # reschedule = serializer.instance
        # Notification.objects.create(
        #     recipient_id=1,  # Admin
        #     sender=self.request.user,
        #     notification_type='general',
        #     title='Class Reschedule Request',
        #     message=f'Reschedule requested for {reschedule.session.schedule.subject} from {reschedule.original_datetime} to {reschedule.new_datetime}'
        # )


class PendingReschedulesView(generics.ListAPIView):
    """List pending reschedule requests for admin"""
    serializer_class = ClassRescheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only admin can view
        if self.request.user.role != 'admin':
            return ClassReschedule.objects.none()
        return ClassReschedule.objects.filter(is_approved=False)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_reschedule(request, reschedule_id):
    """Admin approves a reschedule request"""
    if request.user.role != 'admin':
        return Response(
            {'error': 'Only admin can approve reschedules'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    reschedule = get_object_or_404(ClassReschedule, id=reschedule_id)
    reschedule.approve_reschedule(request.user)
    
    return Response({'message': 'Reschedule approved successfully'})


# Admin Views
class AdminScheduleListView(generics.ListAPIView):
    """Admin view of all schedules"""
    serializer_class = LiveClassScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role != 'admin':
            return LiveClassSchedule.objects.none()
        return LiveClassSchedule.objects.all().order_by('-created_at')


class AdminPaymentListView(generics.ListAPIView):
    """Admin view of all payments"""
    serializer_class = LiveClassPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role != 'admin':
            return LiveClassPayment.objects.none()
        return LiveClassPayment.objects.all().order_by('-initiated_at')


class AdminSessionListView(generics.ListAPIView):
    """Admin view of all sessions"""
    serializer_class = LiveClassSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role != 'admin':
            return LiveClassSession.objects.none()
        return LiveClassSession.objects.all().order_by('-scheduled_datetime')


# Utility Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def schedule_analytics(request, schedule_id):
    """Get analytics for a specific schedule"""
    schedule = get_object_or_404(LiveClassSchedule, schedule_id=schedule_id)
    
    # Check permissions
    user = request.user
    if hasattr(user, 'teacher_profile'):
        if schedule.teacher != user.teacher_profile:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    elif hasattr(user, 'student_profile'):
        if schedule.student != user.student_profile:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    elif user.role != 'admin':
        return Response(
            {'error': 'Access denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Calculate analytics
    sessions = schedule.sessions.all()
    total_sessions = sessions.count()
    completed_sessions = sessions.filter(status='completed').count()
    missed_sessions = sessions.filter(status='missed').count()
    
    active_subscription = schedule.subscriptions.filter(status='active').first()
    
    analytics = {
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'missed_sessions': missed_sessions,
        'attendance_rate': (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
        'demo_completed': schedule.demo_completed,
        'active_subscription': LiveClassSubscriptionSerializer(active_subscription).data if active_subscription else None,
        'total_subscriptions': schedule.subscriptions.count(),
        'total_revenue': sum(sub.amount_paid for sub in schedule.subscriptions.filter(status__in=['active', 'expired']))
    }
    
    return Response(analytics)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def upcoming_classes(request):
    """Get upcoming classes for user"""
    user = request.user
    
    if hasattr(user, 'teacher_profile'):
        schedules = LiveClassSchedule.objects.filter(
            teacher=user.teacher_profile,
            is_active=True
        )
    elif hasattr(user, 'student_profile'):
        schedules = LiveClassSchedule.objects.filter(
            student=user.student_profile,
            is_active=True
        )
    else:
        return Response([])
    
    upcoming = []
    for schedule in schedules:
        next_class = schedule.get_next_class_date()
        if next_class:
            upcoming.append({
                'schedule_id': schedule.schedule_id,
                'subject': schedule.subject,
                'teacher_name': schedule.teacher.full_name,
                'student_name': schedule.student.full_name,
                'scheduled_time': next_class.isoformat(),
                'duration': schedule.class_duration,
                'is_demo': not schedule.demo_completed
            })
    
    # Sort by scheduled time
    upcoming.sort(key=lambda x: x['scheduled_time'])
    
    return Response(upcoming[:10])  # Return next 10 classes
