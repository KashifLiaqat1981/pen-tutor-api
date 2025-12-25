# group_sessions/views.py
from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db.models import Q, Count, Avg
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import GroupSession, GroupSessionEnrollment, AttendanceLog
from .serializers import (
    GroupSessionSerializer, CreateGroupSessionSerializer,
    UpdateGroupSessionSerializer, EnrollmentSerializer,
    CreateEnrollmentSerializer
)
from payments.models import Payment
from meetings.models import Meeting
from authentication.models import User


# ============ GROUP SESSIONS ============

class GroupSessionListView(generics.ListAPIView):
    """List all published group sessions"""
    serializer_class = GroupSessionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = GroupSession.objects.filter(status='published')

        # Filtering
        teacher = self.request.query_params.get('teacher')
        is_free = self.request.query_params.get('free')
        is_upcoming = self.request.query_params.get('upcoming')
        is_live = self.request.query_params.get('live')
        search = self.request.query_params.get('search')

        if teacher:
            queryset = queryset.filter(teacher__username=teacher)
        if is_free and is_free.lower() == 'true':
            queryset = queryset.filter(is_free=True)
        if is_upcoming and is_upcoming.lower() == 'true':
            queryset = queryset.filter(start_time__gt=timezone.now())
        if is_live and is_live.lower() == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                start_time__lte=now,
                end_time__gte=now
            )
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search) |
                Q(tags__icontains=search)
            )

        # Ordering
        order_by = self.request.query_params.get('order_by', 'start_time')
        if order_by in ['start_time', 'price', 'created_at', 'current_enrollments']:
            queryset = queryset.order_by(order_by)

        return queryset


class GroupSessionDetailView(generics.RetrieveAPIView):
    """Get specific group session details"""
    serializer_class = GroupSessionSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        return GroupSession.objects.filter(status='published')


class CreateGroupSessionView(generics.CreateAPIView):
    """Create a new group session (Teacher only)"""
    serializer_class = CreateGroupSessionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()


class TeacherSessionsView(generics.ListAPIView):
    """Get all group sessions created by the logged-in teacher"""
    serializer_class = GroupSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GroupSession.objects.filter(
            teacher=self.request.user
        ).order_by('-start_time')  # Most recent first, or use 'start_time' for upcoming


class UpdateGroupSessionView(generics.UpdateAPIView):
    """Update group session (Teacher only)"""
    serializer_class = UpdateGroupSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        # Teachers can only update their own sessions
        return GroupSession.objects.filter(teacher=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance

        # If publishing for the first time
        if serializer.validated_data.get('status') == 'published' and instance.status != 'published':
            serializer.validated_data['published_at'] = timezone.now()

            # Auto-create meeting if not exists
            if not instance.meeting:
                instance.create_meeting_instance()

        serializer.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_group_session(request, id):
    """Publish a draft session"""
    try:
        session = GroupSession.objects.get(
            id=id,
            teacher=request.user,
            status='draft'
        )

        session.status = 'published'
        session.published_at = timezone.now()
        session.save()

        # Create meeting instance
        if not session.meeting:
            session.create_meeting_instance()

        return Response({
            'success': True,
            'message': 'Session published successfully',
            'session': GroupSessionSerializer(session, context={'request': request}).data
        })

    except GroupSession.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Session not found or you cannot publish it'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_group_session(request, id):
    """Cancel a published session"""
    try:
        session = GroupSession.objects.get(
            id=id,
            teacher=request.user,
            status='published'
        )

        # Can't cancel if it has started
        if session.start_time <= timezone.now():
            return Response({
                'success': False,
                'message': 'Cannot cancel a session that has already started'
            }, status=status.HTTP_400_BAD_REQUEST)

        session.status = 'cancelled'
        session.save()

        # Refund payments
        enrollments = session.enrollments.filter(
            status='enrolled',
            payment__isnull=False
        )
        for enrollment in enrollments:
            # Implement refund logic here
            enrollment.status = 'refunded'
            enrollment.save()

        return Response({
            'success': True,
            'message': 'Session cancelled successfully'
        })

    except GroupSession.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Session not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ============ ENROLLMENTS ============

class EnrollInSessionView(APIView):
    """Enroll in a group session"""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CreateEnrollmentSerializer,
        responses={201: EnrollmentSerializer}
    )
    def post(self, request):
        serializer = CreateEnrollmentSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            with transaction.atomic():
                enrollment = serializer.save()
                session = enrollment.session

                if not session.is_free and session.price > 0:
                    payment = Payment.objects.create(
                        user=request.user,
                        amount=session.price,
                        currency=session.currency,
                        payment_type='group_session',
                        group_session=session,
                        status='pending'
                    )
                    enrollment.payment = payment
                    enrollment.save()

                    return Response({
                        'success': True,
                        'message': 'Enrollment created. Payment required.',
                        'enrollment': EnrollmentSerializer(enrollment).data,
                        'payment': {
                            'id': payment.id,
                            'amount': str(payment.amount),
                            'currency': payment.currency,
                            'payment_url': f'/api/payments/checkout/{payment.id}/'
                        }
                    }, status=status.HTTP_201_CREATED)

                # FREE SESSION
                return Response({
                    'success': True,
                    'message': 'Successfully enrolled in session',
                    'enrollment': EnrollmentSerializer(enrollment).data
                }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class StudentEnrollmentsView(generics.ListAPIView):
    """Get student's enrollments"""
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GroupSessionEnrollment.objects.filter(
            student=self.request.user
        ).select_related('session', 'payment').order_by('-enrolled_at')


class TeacherEnrollmentsView(generics.ListAPIView):
    """Get enrollments for teacher's sessions"""
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GroupSessionEnrollment.objects.filter(
            session__teacher=self.request.user
        ).select_related('session', 'student', 'payment').order_by('-enrolled_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_enrollment(request, enrollment_id):
    """Approve a pending enrollment (Teacher only)"""
    try:
        enrollment = GroupSessionEnrollment.objects.get(
            id=enrollment_id,
            session__teacher=request.user,
            status='pending'
        )

        enrollment.status = 'enrolled'
        enrollment.save()

        return Response({
            'success': True,
            'message': 'Enrollment approved',
            'enrollment': EnrollmentSerializer(enrollment).data
        })

    except GroupSessionEnrollment.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Enrollment not found or cannot be approved'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_enrollment(request, enrollment_id):
    """Cancel an enrollment"""
    try:
        enrollment = GroupSessionEnrollment.objects.get(
            id=enrollment_id,
            student=request.user,
            status__in=['pending', 'enrolled']
        )

        # Check if session has started
        if enrollment.session.start_time <= timezone.now():
            return Response({
                'success': False,
                'message': 'Cannot cancel enrollment after session has started'
            }, status=status.HTTP_400_BAD_REQUEST)

        enrollment.status = 'cancelled'
        enrollment.cancelled_at = timezone.now()
        enrollment.save()

        return Response({
            'success': True,
            'message': 'Enrollment cancelled'
        })

    except GroupSessionEnrollment.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Enrollment not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group_session_meeting(request, session_id):
    """Join a group session meeting – creates a new attendance log entry"""
    try:
        enrollment = GroupSessionEnrollment.objects.get(
            session__id=session_id,
            student=request.user,
            status='enrolled'
        )

        if not enrollment.can_join_meeting:
            return Response({
                'success': False,
                'message': 'Cannot join meeting at this time'
            }, status=status.HTTP_400_BAD_REQUEST)

        session = enrollment.session

        # Create meeting on-demand if not exists
        if not session.meeting:
            meeting = Meeting.objects.create(
                host=session.teacher,
                title=session.title,
                meeting_type='scheduled',
                access_type='private',
                scheduled_time=session.start_time,
                max_participants=session.max_students,
                is_password_required=True,
            )
            session.meeting = meeting
            session.save()
        else:
            meeting = session.meeting

        # === NEW: Create a new attendance log for this join ===
        AttendanceLog.objects.create(enrollment=enrollment)

        return Response({
            'success': True,
            'message': 'Joined meeting successfully',
            'meeting_id': meeting.meeting_id,
            'join_url': f'/api/meetings/join/{meeting.meeting_id}/'
        })

    except GroupSessionEnrollment.DoesNotExist:
        return Response({
            'success': False,
            'message': 'You are not enrolled in this session'
        }, status=status.HTTP_403_FORBIDDEN)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_group_session_meeting(request, session_id):
    """Leave a group session meeting – marks the latest open log as left"""
    try:
        enrollment = GroupSessionEnrollment.objects.get(
            session__id=session_id,
            student=request.user,
            status='enrolled'
        )

        # Find the most recent attendance log that hasn't been marked as left
        open_log = enrollment.attendance_logs.filter(left_at__isnull=True).last()

        if open_log:
            open_log.mark_left()  # Sets left_at, calculates duration_minutes, saves

            # Optional: Update enrollment.attended based on total time
            total_minutes = enrollment.total_attendance_duration
            if total_minutes >= 30:  # or whatever threshold you want
                enrollment.attended = True
                enrollment.save(update_fields=['attended'])

        return Response({
            'success': True,
            'message': 'Left meeting successfully',
            'total_attendance_minutes': enrollment.total_attendance_duration
        })

    except GroupSessionEnrollment.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Enrollment not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ============ PAYMENT WEBHOOK ============

@api_view(['POST'])
@permission_classes([])  # Public endpoint for webhook
def payment_webhook(request):
    """Handle payment webhook to update enrollment status"""
    # This is a simplified version
    # In production, implement proper signature verification

    payment_id = request.data.get('payment_id')
    payment_status = request.data.get('status')

    try:
        payment = Payment.objects.get(id=payment_id)

        if payment_status == 'success':
            payment.is_successful = True
            payment.status = 'completed'
            payment.save()

            # Update enrollment status
            if payment.group_session:
                enrollment = GroupSessionEnrollment.objects.get(
                    session=payment.group_session,
                    student=payment.user,
                    payment=payment
                )
                enrollment.status = 'enrolled'
                enrollment.save()

            return Response({'success': True})

    except Payment.DoesNotExist:
        pass

    return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)