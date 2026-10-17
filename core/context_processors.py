# core/context_processors.py
def organization(request):
    return {
        "organization": request.organization
    }


def unseen_review_counts(request):
    # Drives the navbar's Messages/Applications badges - each count is
    # only queried for users who can read those items at all, so
    # ordinary visitors never pay for it.
    organization = request.organization
    if not organization:
        return {}

    counts = {}
    if request.user.has_perm("core.view_contactmessage"):
        counts["unseen_contact_message_count"] = organization.contact_messages.filter(
            seen_at__isnull=True,
        ).count()
    if request.user.has_perm("core.view_joinrequest"):
        counts["unseen_join_request_count"] = organization.join_requests.filter(
            seen_at__isnull=True,
        ).count()
    return counts




def unread_inbox_count(request):
    # The My Account menu's Inbox count.
    if not request.user.is_authenticated:
        return {}
    return {"unread_inbox_count": request.user.inbox_deliveries.filter(read_at__isnull=True, hidden_at__isnull=True).count()}
