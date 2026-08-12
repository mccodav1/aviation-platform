from django.utils import timezone

from .models import Meeting


def get_next_meeting(organization):
    return (
        organization.meetings
        .filter(
            starts_at__gte=timezone.now(),
            is_cancelled=False,
        )
        .order_by("starts_at")
        .first()
    )