from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MeetingForm
from .models import Meeting
from .services import get_past_or_cancelled_meetings, get_upcoming_meetings


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
