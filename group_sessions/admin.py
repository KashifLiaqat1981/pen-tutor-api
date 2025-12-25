# group_sessions/admin.py
from django.contrib import admin
from .models import GroupSession, GroupSessionEnrollment, AttendanceLog

@admin.register(GroupSession)
class GroupSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'teacher', 'start_time', 'status', 'current_enrollments', 'price']
    list_filter = ['status', 'is_free', 'created_at']
    search_fields = ['title', 'description', 'teacher__username']
    readonly_fields = ['created_at', 'updated_at', 'current_enrollments']
    fieldsets = [
        ('Basic Information', {
            'fields': ['teacher', 'title', 'description', 'short_description']
        }),
        ('Session Details', {
            'fields': ['subject', 'tags', 'starting_date', 'days', 'start_time', 'class_duration', 'session_duration']
        }),
        ('Capacity & Pricing', {
            'fields': ['max_students', 'min_students', 'current_enrollments', 'currency', 'price', 'is_free']
        }),
        ('Meeting', {
            'fields': ['meeting']
        }),
        ('Status & Visibility', {
            'fields': ['status', 'is_featured', 'is_private', 'requires_approval']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'published_at']
        }),
    ]

@admin.register(GroupSessionEnrollment)
class GroupSessionEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['session', 'student', 'status', 'enrolled_at', 'attended']
    list_filter = ['status', 'attended', 'enrolled_at']
    search_fields = ['session__title', 'student__username']
    readonly_fields = ['enrolled_at']


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = [
        'enrollment', 'student', 'joined_at', 'left_at', 'duration_minutes'
    ]
    list_filter = ['joined_at', 'left_at']
    search_fields = ['enrollment__student__username', 'enrollment__session__title']
    readonly_fields = ['enrollment', 'joined_at', 'left_at', 'duration_minutes']

    def student(self, obj):
        return obj.enrollment.student.get_full_name() or obj.enrollment.student.username
    student.short_description = 'Student'