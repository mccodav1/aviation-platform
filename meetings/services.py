from django.db.models import Q
from django.utils import timezone

from .models import Event


def get_next_meeting(organization):
    return (
        organization.events
        .filter(
            event_type=Event.TYPE_MEETING,
            starts_at__gte=timezone.now(),
            is_cancelled=False,
        )
        .order_by("starts_at")
        .first()
    )


def get_upcoming_events(organization, event_type=None):
    events = organization.events.filter(starts_at__gte=timezone.now(), is_cancelled=False)
    if event_type:
        events = events.filter(event_type=event_type)
    return events.order_by("starts_at")


def get_upcoming_meetings(organization):
    return get_upcoming_events(organization, event_type=Event.TYPE_MEETING)


def get_past_or_cancelled_events(organization, event_type=None):
    # An event moves here once it's happened OR once it's cancelled
    # (even if it was in the future) - cancelled events stay visible
    # here, flagged, rather than disappearing.
    events = organization.events.filter(Q(starts_at__lt=timezone.now()) | Q(is_cancelled=True))
    if event_type:
        events = events.filter(event_type=event_type)
    return events.order_by("-starts_at")


def get_past_or_cancelled_meetings(organization):
    return get_past_or_cancelled_events(organization, event_type=Event.TYPE_MEETING)


def get_feed_events(organization, event_type=None):
    # Unlike get_upcoming_events, this deliberately includes cancelled
    # events that are still in the future: the .ics feed represents them
    # with STATUS:CANCELLED (see meetings/ics.py) so a subscribed
    # calendar app can update its copy of the event instead of it just
    # disappearing on the next refresh.
    events = organization.events.filter(starts_at__gte=timezone.now())
    if event_type:
        events = events.filter(event_type=event_type)
    return events.order_by("starts_at")


def get_feed_meetings(organization):
    return get_feed_events(organization, event_type=Event.TYPE_MEETING)
