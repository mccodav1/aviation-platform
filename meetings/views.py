from django.shortcuts import render

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
