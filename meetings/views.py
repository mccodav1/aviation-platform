from pathlib import Path

from django.contrib.auth.decorators import login_required, permission_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .forms import EventAgendaForm, EventForm, EventMinutesForm
from .ics import build_event_ics, build_events_feed_ics
from .models import Event
from .services import (
    get_feed_events,
    get_feed_meetings,
    get_past_or_cancelled_meetings,
    get_upcoming_events,
    get_upcoming_meetings,
)


def meeting_detail(request, pk):
    # Public, same as meeting_list - no reason to require an account just
    # to see the date, location, and description of a meeting.
    meeting = get_object_or_404(Event, pk=pk, organization=request.organization)
    return render(request, "app/meeting_detail.html", {"meeting": meeting})


def meeting_list(request):
    organization = request.organization

    upcoming_meetings = get_upcoming_meetings(organization) if organization else []
    past_or_cancelled_meetings = get_past_or_cancelled_meetings(organization) if organization else []

    return render(
        request,
        "app/meetings.html",
        {
            "upcoming_meetings": upcoming_meetings,
            "past_or_cancelled_meetings": past_or_cancelled_meetings,
        },
    )


def event_list(request):
    # Every event type, not just meetings - the calendar page this feeds
    # is meetings.html's general-purpose sibling (see app/events.html).
    organization = request.organization

    upcoming_events = get_upcoming_events(organization) if organization else []

    return render(
        request,
        "app/events.html",
        {
            "upcoming_events": upcoming_events,
        },
    )


@login_required
@permission_required("meetings.add_event", raise_exception=True)
def meeting_create(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organization = request.organization
            event.save()
            return redirect("core:meetings")
    else:
        form = EventForm(initial={"event_type": Event.TYPE_MEETING})

    return render(request, "app/meeting_form.html", {"form": form})


@login_required
@permission_required("meetings.change_event", raise_exception=True)
@require_POST
def meeting_toggle_cancelled(request, pk):
    # Cancelling is reversible on purpose - a permanent delete stays an
    # /admin-only action (Club Officers already have that permission
    # there if an event genuinely needs to be erased, e.g. a mistaken
    # duplicate entry).
    meeting = get_object_or_404(Event, pk=pk, organization=request.organization)
    meeting.is_cancelled = not meeting.is_cancelled
    meeting.save(update_fields=["is_cancelled"])
    return redirect("core:meetings")


def _manage_meeting_file(request, pk, form_class, field_label):
    meeting = get_object_or_404(Event, pk=pk, organization=request.organization)

    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=meeting)
        if form.is_valid():
            form.save()
            return redirect("core:meetings")
    else:
        form = form_class(instance=meeting)

    return render(
        request,
        "app/meeting_attachment_form.html",
        {"form": form, "meeting": meeting, "field_label": field_label},
    )


def _download_meeting_file(request, pk, field_name):
    meeting = get_object_or_404(Event, pk=pk, organization=request.organization)
    file_field = getattr(meeting, field_name)

    if not file_field:
        raise Http404

    return FileResponse(
        file_field.open("rb"),
        filename=Path(file_field.name).name,
        as_attachment=False,  # open in the browser rather than force a download
    )


@login_required
@permission_required("meetings.change_event", raise_exception=True)
def meeting_agenda_manage(request, pk):
    return _manage_meeting_file(request, pk, EventAgendaForm, "Agenda")


@login_required
@permission_required("meetings.change_event", raise_exception=True)
def meeting_minutes_manage(request, pk):
    return _manage_meeting_file(request, pk, EventMinutesForm, "Minutes")


@login_required
def meeting_agenda_download(request, pk):
    # Any signed-in user (Member and up) - not gated by meetings.change_event.
    return _download_meeting_file(request, pk, "agenda")


@login_required
def meeting_minutes_download(request, pk):
    return _download_meeting_file(request, pk, "minutes")


def meeting_ics(request, pk):
    # Public, same as the meetings list itself - no reason to require an
    # account just to put a public meeting on your own calendar.
    meeting = get_object_or_404(Event, pk=pk, organization=request.organization)
    ics = build_event_ics(meeting)
    response = HttpResponse(ics, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{slugify(meeting.title)}.ics"'
    return response


def meetings_ics_feed(request):
    organization = request.organization
    meetings = get_feed_meetings(organization) if organization else []
    calendar_name = f"{organization.name} Meetings" if organization else "Meetings"

    ics = build_events_feed_ics(meetings, calendar_name)
    response = HttpResponse(ics, content_type="text/calendar")
    response["Content-Disposition"] = 'inline; filename="meetings.ics"'
    return response


def events_ics_feed(request):
    organization = request.organization
    events = get_feed_events(organization) if organization else []
    calendar_name = f"{organization.name} Events" if organization else "Events"

    ics = build_events_feed_ics(events, calendar_name)
    response = HttpResponse(ics, content_type="text/calendar")
    response["Content-Disposition"] = 'inline; filename="events.ics"'
    return response
