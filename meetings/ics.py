import datetime

from django.utils import timezone
from icalendar import Calendar, Event

# No explicit meeting length in the model - a generic default keeps every
# calendar entry well-formed (most calendar apps expect DTEND/DURATION)
# without needing to ask officers to estimate an end time.
DEFAULT_MEETING_DURATION = datetime.timedelta(hours=1)


def _meeting_to_vevent(meeting):
    event = Event()

    # Stable across regenerations so a calendar app refreshing a
    # subscription updates the same entry (e.g. once it's cancelled)
    # rather than creating a duplicate. Keyed off the organization's UUID
    # rather than a real domain, since this project has no configured
    # public hostname (see django.contrib.sites, unused here).
    event.add("uid", f"meeting-{meeting.pk}@{meeting.organization_id}.aviation-platform")

    summary = meeting.title
    if meeting.is_cancelled:
        summary = f"CANCELLED: {summary}"
    event.add("summary", summary)

    event.add("dtstart", meeting.starts_at)
    event.add("dtend", meeting.starts_at + DEFAULT_MEETING_DURATION)
    event.add("dtstamp", timezone.now())

    if meeting.location:
        event.add("location", meeting.location)

    if meeting.description:
        event.add("description", meeting.description)

    if meeting.is_cancelled:
        # Lets a subscribed calendar app mark the existing entry
        # cancelled in place, instead of it just quietly vanishing (or
        # not, depending on the client) next time the feed is refetched.
        event.add("status", "CANCELLED")

    return event


def _new_calendar():
    cal = Calendar()
    cal.add("prodid", "-//aviation-platform//meetings//")
    cal.add("version", "2.0")
    return cal


def build_meeting_ics(meeting):
    """A single-event .ics for the 'Add to Calendar' link on one meeting."""
    cal = _new_calendar()
    cal.add_component(_meeting_to_vevent(meeting))
    return cal.to_ical()


def build_meetings_feed_ics(meetings, calendar_name):
    """A multi-event .ics for the all-meetings subscription feed."""
    cal = _new_calendar()
    cal.add("x-wr-calname", calendar_name)
    cal.add("method", "PUBLISH")
    for meeting in meetings:
        cal.add_component(_meeting_to_vevent(meeting))
    return cal.to_ical()
