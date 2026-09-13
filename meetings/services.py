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


def get_feed_meetings(organization):
    # Unlike get_upcoming_meetings, this deliberately includes cancelled
    # meetings that are still in the future: the .ics feed represents
    # them with STATUS:CANCELLED (see meetings/ics.py) so a subscribed
    # calendar app can update its copy of the event instead of it just
    # disappearing on the next refresh.
    return (
        organization.meetings
        .filter(starts_at__gte=timezone.now())
        .order_by("starts_at")
    )