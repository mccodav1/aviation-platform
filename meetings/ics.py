import datetime

from django.utils import timezone
from icalendar import Calendar, Event as VEvent

# No explicit event length in the model - a generic default keeps every
# calendar entry well-formed (most calendar apps expect DTEND/DURATION)
# without needing to ask officers to estimate an end time. Not yet
# type-aware (an airshow realistically runs longer than an hour) - flat
# for every event_type until there's a real need to vary it.
DEFAULT_EVENT_DURATION = datetime.timedelta(hours=1)


def _event_to_vevent(event):
    vevent = VEvent()

    # Stable across regenerations so a calendar app refreshing a
    # subscription updates the same entry (e.g. once it's cancelled)
    # rather than creating a duplicate. Keyed off the organization's UUID
    # rather than a real domain, since this project has no configured
    # public hostname (see django.contrib.sites, unused here).
    vevent.add("uid", f"event-{event.pk}@{event.organization_id}.aviation-platform")

    summary = event.title
    if event.is_cancelled:
        summary = f"CANCELLED: {summary}"
    vevent.add("summary", summary)

    vevent.add("dtstart", event.starts_at)
    vevent.add("dtend", event.starts_at + DEFAULT_EVENT_DURATION)
    vevent.add("dtstamp", timezone.now())

    if event.location:
        vevent.add("location", event.location)

    if event.description:
        vevent.add("description", event.description)

    if event.is_cancelled:
        # Lets a subscribed calendar app mark the existing entry
        # cancelled in place, instead of it just quietly vanishing (or
        # not, depending on the client) next time the feed is refetched.
        vevent.add("status", "CANCELLED")

    return vevent


def _new_calendar():
    cal = Calendar()
    cal.add("prodid", "-//aviation-platform//events//")
    cal.add("version", "2.0")
    return cal


def build_event_ics(event):
    """A single-event .ics for the 'Add to Calendar' link on one event."""
    cal = _new_calendar()
    cal.add_component(_event_to_vevent(event))
    return cal.to_ical()


def build_events_feed_ics(events, calendar_name):
    """A multi-event .ics for an events subscription feed."""
    cal = _new_calendar()
    cal.add("x-wr-calname", calendar_name)
    cal.add("method", "PUBLISH")
    for event in events:
        cal.add_component(_event_to_vevent(event))
    return cal.to_ical()
