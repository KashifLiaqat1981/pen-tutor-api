# activity/admin.py
from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'email', 'user_role', 'action', 'module', 'page_url')
    list_filter = ('module', 'user__role', 'timestamp')
    search_fields = ('user__username', 'user__email', 'action', 'module')
    readonly_fields = ('timestamp', 'user', 'action', 'module', 'page_url', 'user_agent', 'extra_info')
    ordering = ('-timestamp',)

    def user_email(self, obj):
        return obj.user.email if obj.user else '-'

    def user_role(self, obj):
        return obj.user.role if obj.user else '-'

    def has_add_permission(self, request, obj=None):
        # Logs should not be manually added
        return False

    def has_change_permission(self, request, obj=None):
        # Logs are read-only
        return False
