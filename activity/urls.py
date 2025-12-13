from django.urls import path
from .views import ActivityLogViewSet

activity_log_list = ActivityLogViewSet.as_view({'get': 'list'})
activity_log_detail = ActivityLogViewSet.as_view({'get': 'retrieve'})

urlpatterns = [
    path('activity-logs/', activity_log_list, name='activity-logs-list'),
    path('activity-logs/<uuid:pk>/', activity_log_detail, name='activity-logs-detail'),
]