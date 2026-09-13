from pathlib import Path

from django.contrib.auth.decorators import login_required, permission_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .forms import MeetingAgendaForm, MeetingForm, MeetingMinutesForm
from .ics import build_meeting_ics, build_meetings_feed_ics
from .models import Meeting
from .services import get_feed_meetings, get_past_or_cancelled_meetings, get_upcoming_meetings


def meeting_detail(request, pk):
    # Public, same as meeting_list - no reason to require an account just
    # to see the date, location, and description of a meeting.
    meeting = get_object_or_404(Meeting, pk=pk, organization=request.organization)
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


@login_required
@permission_required("meetings.add_meeting", raise_exception=True)
def meeting_create(request):
    if request.method == "POST":
        form = MeetingForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.organization = request.organization
            meeting.save()
            return redirect("core:meetings")
    else:
        form = MeetingForm()

    return render(request, "app/meeting_form.html", {"form": form})


@login_required
@permission_required("meetings.change_meeting", raise_exception=True)
@require_POST
def meeting_toggle_cancelled(request, pk):
    # Cancelling is reversible on purpose - a permanent delete stays an
    # /admin-only action (Club Officers already have that permission
    # there if a meeting genuinely needs to be erased, e.g. a mistaken
    # duplicate entry).
    meeting = get_object_or_404(Meeting, pk=pk, organization=request.organization)
    meeting.is_cancelled = not meeting.is_cancelled
    meeting.save(update_fields=["is_cancelled"])
    return redirect("core:meetings")


def _manage_meeting_file(request, pk, form_class, field_label):
    meeting = get_object_or_404(Meeting, pk=pk, organization=request.organization)

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
    meeting = get_object_or_404(Meeting, pk=pk, organization=request.organization)
    file_field = getattr(meeting, field_name)

    if not file_field:
        raise Http404

    return FileResponse(
        file_field.open("rb"),
        filename=Path(file_field.name).name,
        as_attachment=False,  # open in the browser rather than force a download
    )


@login_required
@permission_required("meetings.change_meeting", raise_exception=True)
def meeting_agenda_manage(request, pk):
    return _manage_meeting_file(request, pk, MeetingAgendaForm, "Agenda")


@login_required
@permission_required("meetings.change_meeting", raise_exception=True)
def meeting_minutes_manage(request, pk):
    return _manage_meeting_file(request, pk, MeetingMinutesForm, "Minutes")


@login_required
def meeting_agenda_download(request, pk):
    # Any signed-in user (Member and up) - not gated by meetings.change_meeting.
    return _download_meeting_file(request, pk, "agenda")


@login_required
def meeting_minutes_download(request, pk):
    return _download_meeting_file(request, pk, "minutes")


def meeting_ics(request, pk):
    # Public, same as the meetings list itself - no reason to require an
    # account just to put a public meeting on your own calendar.
    meeting = get_object_or_404(Meeting, pk=pk, organization=request.organization)
    ics = build_meeting_ics(meeting)
    response = HttpResponse(ics, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{slugify(meeting.title)}.ics"'
    return response


def meetings_ics_feed(request):
    organization = request.organization
    meetings = get_feed_meetings(organization) if organization else []
    calendar_name = f"{organization.name} Meetings" if organization else "Meetings"

    ics = build_meetings_feed_ics(meetings, calendar_name)
    response = HttpResponse(ics, content_type="text/calendar")
    response["Content-Disposition"] = 'inline; filename="meetings.ics"'
    return response
