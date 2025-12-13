# activity/utils.py
from .models import ActivityLog
from django.utils import timezone

def log_activity(user=None, action="", module="", request=None, extra_info=None):

    user_agent = None
    page_url = None

    if request:
        user_agent = request.META.get('HTTP_USER_AGENT')
        page_url = request.build_absolute_uri()

    ActivityLog.objects.create(
        user=user,
        action=action,
        module=module,
        page_url=page_url,
        user_agent=user_agent,
        extra_info=extra_info or {},
        timestamp=timezone.now()
    )