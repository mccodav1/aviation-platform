# core/context_processors.py
def organization(request):
    return {
        "organization": request.organization
    }


def unseen_contact_messages(request):
    # Drives the navbar's messages badge - only queried for users who can
    # read the messages at all, so ordinary visitors never pay for it.
    if not request.organization or not request.user.has_perm("core.view_contactmessage"):
        return {}
    return {
        "unseen_contact_message_count": request.organization.contact_messages.filter(
            seen_at__isnull=True,
        ).count(),
    }


