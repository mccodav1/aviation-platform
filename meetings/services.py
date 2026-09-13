from django.db.models import Q
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


def get_upcoming_meetings(organization):
    return (
        organization.meetings
        .filter(starts_at__gte=timezone.now(), is_cancelled=False)
        .order_by("starts_at")
    )


def get_past_or_cancelled_meetings(organization):
    # A meeting moves here once it's happened OR once it's cancelled
    # (even if it was in the future) - cancelled meetings stay visible
    # here, flagged, rather than disappearing.
    return (
        organization.meetings
        .filter(Q(starts_at__lt=timezone.now()) | Q(is_cancelled=True))
        .order_by("-starts_at")
    )