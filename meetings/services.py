import calendar
from datetime import date, datetime, time, timedelta

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


def get_month_calendar(organization, year, month):
    """Builds the week/day grid for the home page's calendar widget,
    with each day's events already attached - the template just walks
    the structure, it doesn't query or do date math itself.

    starts_at is stored as an aware UTC instant (see the org's own
    TIME_ZONE-vs-UTC note on Event.__str__) - month boundaries and each
    event's day bucket are both computed in local time, so an event
    just before/after local midnight lands on the calendar day a
    person here would actually expect, not whatever day it happened to
    be in UTC.
    """
    month_start = date(year, month, 1)
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    events_by_day = {}
    if organization:
        events = organization.events.filter(
            starts_at__gte=timezone.make_aware(datetime.combine(month_start, time.min)),
            starts_at__lt=timezone.make_aware(datetime.combine(next_month_start, time.min)),
        ).order_by("starts_at")
        for event in events:
            events_by_day.setdefault(timezone.localtime(event.starts_at).date(), []).append(event)

    today = timezone.localdate()
    weeks = []
    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(year, month):
        weeks.append([
            {
                "date": day,
                "in_month": day.month == month,
                "is_today": day == today,
                "events": events_by_day.get(day, []),
            }
            for day in week
        ])

    prev_month_end = month_start - timedelta(days=1)

    return {
        "weeks": weeks,
        "month_label": month_start.strftime("%B %Y"),
        "prev_month": f"{prev_month_end.year:04d}-{prev_month_end.month:02d}",
        "next_month": f"{next_month_start.year:04d}-{next_month_start.month:02d}",
    }
