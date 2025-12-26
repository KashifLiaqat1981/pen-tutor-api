from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import ChatRoom, Message, MessageRead
from job_board.models import JobApplication

# ---------------- ChatRoom Admin ----------------

class MessageInline(admin.TabularInline):
    model = Message
    fk_name = 'room'
    extra = 0
    readonly_fields = ['sender', 'content', 'created_at']
    fields = ['sender', 'content', 'message_type', 'created_at']
    show_change_link = True

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'created_by_name', 'participant_count', 'job_link', 'created_at']
    search_fields = ['name', 'description', 'participants__username', 'participants__first_name', 'participants__last_name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['created_by']
    inlines = [MessageInline]

    def created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username
    created_by_name.short_description = 'Created By'

    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'

    def job_link(self, obj):
        applications = JobApplication.objects.filter(job_post_id=obj.job_id)
        links = []
        for app in applications:
            url = reverse("admin:job_board_jobapplication_change", args=[app.id])
            links.append(f'<a href="{url}">{app.teacher.user.get_full_name()}</a>')
        return format_html(", ".join(links))

    job_link.short_description = "Applications"

# ---------------- Message Admin ----------------

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'room', 'sender_name', 'message_type', 'content_preview', 'created_at']
    search_fields = ['content', 'sender__username', 'sender__first_name', 'sender__last_name']
    readonly_fields = ['sender', 'created_at', 'updated_at', 'room']
    raw_id_fields = ['room', 'sender']

    def sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username
    sender_name.short_description = 'Sender'

    def content_preview(self, obj):
        if obj.has_forbidden_content:
            return format_html(
                '<span style="color:red; font-weight:bold;">[BLOCKED]</span> {}',
                obj.content[:40] if obj.content else ''
            )
        return (obj.content[:50] + '...') if obj.content and len(obj.content) > 50 else obj.content

    content_preview.short_description = 'Content'

# Optionally, you can register MessageRead if needed
@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'user', 'read_at']
    readonly_fields = ['message', 'user', 'read_at']

    def message_id(self, obj):
        return obj.message.id
    message_id.short_description = 'Message ID'
