"""
Context processor for Scholarship Management — injects unread notification count.
"""
from .models import Notification, StudentProfile


def scholarship_context(request):
    if not request.user.is_authenticated:
        return {}
    unread_count = Notification.objects.filter(recipient=request.user, read=False).count()
    try:
        profile = request.user.scholarship_profile
        stage_1_complete = profile.is_stage_1_complete
    except StudentProfile.DoesNotExist:
        stage_1_complete = False

    return {
        'sm_unread_notifications': unread_count,
        'sm_stage_1_complete': stage_1_complete,
    }
