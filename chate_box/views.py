# views.py
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils import timezone
from datetime import datetime

from .models import ChatRoom, Message, MessageRead
from .serializers import ChatRoomSerializer, MessageSerializer, JobApplicationChatSerializer
from job_board.models import JobApplication, JobPost
from rest_framework.exceptions import PermissionDenied, ValidationError
from authentication.models import User


def parse_time(value):
    return datetime.strptime(value, "%H:%M").time()


# ---------------- Chat Rooms ----------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_room_list(request):
    user = request.user
    queryset = ChatRoom.objects.filter(
        Q(participants=user) | Q(created_by=user)
    ).distinct().prefetch_related(
        'participants',
        'created_by',
        Prefetch('messages', queryset=Message.objects.select_related('sender'))
    )

    serializer = ChatRoomSerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_room_detail(request, pk):
    user = request.user
    room = get_object_or_404(ChatRoom, id=pk)
    if not (room.participants.filter(id=user.id).exists() or room.created_by == user):
        raise PermissionDenied("You are not a participant of this room")

    serializer = ChatRoomSerializer(room, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_participant(request, pk):
    room = get_object_or_404(ChatRoom, id=pk)
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(id=user_id)
        room.participants.add(user)
        return Response({'message': 'Participant added successfully'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_participant(request, pk):
    room = get_object_or_404(ChatRoom, id=pk)
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(id=user_id)
        room.participants.remove(user)
        return Response({'message': 'Participant removed successfully'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_room_messages(request, pk):
    user = request.user
    room = get_object_or_404(ChatRoom, id=pk)
    if not (room.participants.filter(id=user.id).exists() or room.created_by == user):
        raise PermissionDenied("You are not a participant of this room")

    messages = room.messages.filter(status__in=['sent', 'delivered', 'read']).select_related('sender').prefetch_related(
        'read_by__user')

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 50))
    start = (page - 1) * page_size
    end = start + page_size

    paginated_messages = messages[start:end]
    serializer = MessageSerializer(paginated_messages, many=True, context={'request': request})
    return Response({
        'messages': serializer.data,
        'total_count': messages.count(),
        'page': page,
        'has_next': end < messages.count()
    })


# ---------------- Messages ----------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    room_id = request.data.get('room')
    if not room_id:
        return Response({'error': 'room is required'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    try:
        room = ChatRoom.objects.get(id=room_id, participants=user)
    except ChatRoom.DoesNotExist:
        return Response({'error': 'Room not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    serializer = MessageSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(sender=user)
        room.updated_at = timezone.now()
        room.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_message_read(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    if not message.room.participants.filter(id=request.user.id).exists():
        raise PermissionDenied("Access denied")
    MessageRead.objects.get_or_create(message=message, user=request.user)
    return Response({'message': 'Message marked as read'})


# ---------------- Job Applications ----------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_applications_list(request):
    user = request.user
    if hasattr(user, 'teacher_profile'):
        queryset = JobApplication.objects.filter(teacher=user.teacher_profile).select_related('job_post', 'chat_room')
    elif hasattr(user, 'student_profile'):
        queryset = JobApplication.objects.filter(job_post__student=user.student_profile).select_related('teacher',
                                                                                                        'job_post',
                                                                                                        'chat_room')
    else:
        queryset = JobApplication.objects.none()

    serializer = JobApplicationChatSerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data)


class JobApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Apply for a job OR ensure 1:1 chat room exists."""
        job_post_id = request.data.get('job_post')
        job_post = get_object_or_404(JobPost, id=job_post_id)
        user = request.user

        # -------------------------
        # Resolve application
        # -------------------------
        if user.role == 'teacher':
            teacher_profile = user.teacher_profile
            application, created = JobApplication.objects.get_or_create(
                job_post=job_post,
                teacher=teacher_profile
            )

        elif user.role == 'student':
            student_profile = user.student_profile
            application = JobApplication.objects.filter(
                job_post=job_post,
                job_post__student=student_profile
            ).first()

            if not application:
                return Response(
                    {'error': 'No application exists for this job.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'error': 'Only teachers or students can use this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # -------------------------
        # Ensure chat room exists
        # -------------------------
        if not application.chat_room:
            room = ChatRoom.objects.create(
                name=f"Application: {job_post.title}",
                room_type='job',
                description=f"Chat for job application #{application.id}",
                job_id=job_post.id,
                created_by=user
            )

            # Correct participants
            room.participants.add(
                application.teacher.user,
                job_post.student.user
            )

            application.chat_room = room
            application.save()

        serializer = JobApplicationChatSerializer(application, context={'request': request})
        data = serializer.data
        data['can_chat'] = True

        return Response(data, status=status.HTTP_201_CREATED)

    def get(self, request, job_post_id):
        """Retrieve application + chat availability."""
        user = request.user

        if user.role == 'teacher':
            application = JobApplication.objects.filter(
                job_post_id=job_post_id,
                teacher=user.teacher_profile
            ).first()

        elif user.role == 'student':
            application = JobApplication.objects.filter(
                job_post_id=job_post_id,
                job_post__student=user.student_profile
            ).first()
        else:
            return Response(
                {'error': 'Only teachers or students can use this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not application:
            return Response(
                {'error': 'No application found for this job.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = JobApplicationChatSerializer(application, context={'request': request})
        data = serializer.data
        data['can_chat'] = bool(application.chat_room)

        return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finalize_agreement(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)
    user = request.user

    # Check if user is part of this application
    is_teacher = hasattr(user, 'teacher_profile') and user.teacher_profile == application.teacher
    is_student = hasattr(user, 'student_profile') and user.student_profile == application.job_post.student
    if not (is_teacher or is_student):
        raise PermissionDenied("You are not part of this application")

    errors = {}

    finalized_days = request.data.get('finalized_days', [])
    finalized_time_start = request.data.get('finalized_time_start')
    finalized_time_end = request.data.get('finalized_time_end')
    finalized_budget = request.data.get('finalized_budget')
    demo_class_time = request.data.get('demo_class_time')

    if not finalized_days:
        errors['finalized_days'] = 'Please select at least one day.'

    if not finalized_time_start:
        errors['finalized_time_start'] = 'Start time is required.'

    if not finalized_time_end:
        errors['finalized_time_end'] = 'End time is required.'

    if not finalized_budget:
        errors['finalized_budget'] = 'Budget is required.'

    if not demo_class_time:
        errors['demo_class_time'] = 'Demo class time is required.'

    if errors:
        raise ValidationError(errors)

    if is_teacher:
        application.teacher_finalized_days = finalized_days
        application.teacher_finalized_time_start = parse_time(finalized_time_start)
        application.teacher_finalized_time_end = parse_time(finalized_time_end)
        application.teacher_finalized_budget = finalized_budget
        application.teacher_demo_class_time = demo_class_time
        application.teacher_finalized = True
    else:
        application.student_finalized_days = finalized_days
        application.student_finalized_time_start = parse_time(finalized_time_start)
        application.student_finalized_time_end = parse_time(finalized_time_end)
        application.student_finalized_budget = finalized_budget
        application.student_demo_class_time = demo_class_time
        application.student_finalized = True

    # Check if both finalized
    if application.teacher_finalized and application.student_finalized:
        # You can implement the validation logic here similar to your original ViewSet
        application.finalized_days = application.teacher_finalized_days
        application.finalized_time_start = application.teacher_finalized_time_start
        application.finalized_time_end = application.teacher_finalized_time_end
        application.finalized_budget = application.teacher_finalized_budget
        application.demo_class_time = application.teacher_demo_class_time
        application.is_finalized = True
        application.finalized_at = timezone.now()
        application.status = 'accepted'
        application.job_post.status = 'accepted'
        application.job_post.selected_teacher = application.teacher
        application.job_post.save()
        # You can also send a finalization message in chat

    application.save()
    serializer = JobApplicationChatSerializer(application, context={'request': request})
    return Response({'message': 'Agreement finalized', 'application': serializer.data})
