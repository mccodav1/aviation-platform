# meetings/context_processors.py

from core.models import InfoPanel

from .services import get_next_meeting


def meetings(request):
    organization = request.organization

    if not organization:
        return {}

    show_next_meeting = organization.enabled_info_panels.filter(
        panel_type=InfoPanel.TYPE_NEXT_MEETING,
    ).exists()

    if not show_next_meeting:
        return {}

    return {
        "next_meeting": get_next_meeting(organization),
    }