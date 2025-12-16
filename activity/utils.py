# activity/utils.py
from .models import ActivityLog
from django.utils import timezone

def log_activity(user=None, email=None, action="", module="", request=None, extra_info=None):

    user_agent = request.META.get('HTTP_USER_AGENT') if request else None
    page_url = request.build_absolute_uri() if request else None

    ActivityLog.objects.create(
        user=user,
        email=email if user is None else user.email,  # use anonymous email if no user
        action=action,
        module=module,
        page_url=page_url,
        user_agent=user_agent,
        extra_info=extra_info or {},
        timestamp=timezone.now()
    )