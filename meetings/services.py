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
    # Includes cancelled meetings (flagged in the template) so a
    # cancellation is visible rather than the meeting just disappearing.
    return (
        organization.meetings
        .filter(starts_at__gte=timezone.now())
        .order_by("starts_at")
    )


def get_past_meetings(organization):
    return (
        organization.meetings
        .filter(starts_at__lt=timezone.now())
        .order_by("-starts_at")
    )