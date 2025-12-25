from django.urls import path
from . import views

urlpatterns = [
    # Chat rooms
    path('chat-rooms/', views.chat_room_list),
    path('chat-rooms/<int:pk>/', views.chat_room_detail),
    path('chat-rooms/<int:pk>/messages/', views.chat_room_messages),
    path('chat-rooms/<int:pk>/add-participant/', views.add_participant),
    path('chat-rooms/<int:pk>/remove-participant/', views.remove_participant),

    # Messages
    path('messages/send/', views.send_message),
    path('messages/<int:message_id>/mark-read/', views.mark_message_read),

    # Job applications
    path('job-applications/', views.job_applications_list),
    path('job-applications/apply/', views.apply_for_job),
    path('job-applications/<int:application_id>/finalize/', views.finalize_agreement),
]