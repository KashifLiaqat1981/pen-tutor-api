# group_sessions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'group_sessions'

urlpatterns = [
    # Group Sessions
    path('sessions/', views.GroupSessionListView.as_view(), name='session-list'),
    path('sessions/create/', views.CreateGroupSessionView.as_view(), name='session-create'),
    path('sessions/my/', views.TeacherSessionsView.as_view(), name='my-sessions'),
    path('sessions/<uuid:id>/', views.GroupSessionDetailView.as_view(), name='session-detail'),
    path('sessions/<uuid:id>/update/', views.UpdateGroupSessionView.as_view(), name='session-update'),
    path('sessions/<uuid:id>/publish/', views.publish_group_session, name='session-publish'),
    path('sessions/<uuid:id>/cancel/', views.cancel_group_session, name='session-cancel'),

    # Enrollments
    path('enroll/', views.EnrollInSessionView.as_view(), name='enroll'),
    path('enrollments/my/', views.StudentEnrollmentsView.as_view(), name='my-enrollments'),
    path('enrollments/teacher/', views.TeacherEnrollmentsView.as_view(), name='teacher-enrollments'),
    path('enrollments/<uuid:enrollment_id>/approve/', views.approve_enrollment, name='approve-enrollment'),
    path('enrollments/<uuid:enrollment_id>/cancel/', views.cancel_enrollment, name='cancel-enrollment'),

    # Meeting Integration
    path('sessions/<uuid:session_id>/join-meeting/', views.join_group_session_meeting, name='join-meeting'),
    path('sessions/<uuid:session_id>/leave-meeting/', views.leave_group_session_meeting, name='leave-meeting'),

    # Webhooks
    path('webhook/payment/', views.payment_webhook, name='payment-webhook'),
]