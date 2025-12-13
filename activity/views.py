# activity/views.py
from rest_framework import viewsets, filters
from .models import ActivityLog
from .serializers import ActivityLogSerializer
from .permissions import IsAdminOrSubAdmin

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminOrSubAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'user__email', 'action', 'module']
    ordering_fields = ['timestamp']
