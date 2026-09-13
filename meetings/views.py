from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from .forms import MeetingForm
from .services import get_past_meetings, get_upcoming_meetings


def meeting_list(request):
    organization = request.organization

    upcoming_meetings = get_upcoming_meetings(organization) if organization else []
    past_meetings = get_past_meetings(organization) if organization else []

    return render(
        request,
        "app/meetings.html",
        {
            "upcoming_meetings": upcoming_meetings,
            "past_meetings": past_meetings,
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
