import logging
from datetime import date
from pathlib import Path

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import redirect_to_login
from django.core.mail import send_mail
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views.decorators.http import require_POST

from meetings.services import get_month_calendar, get_next_meeting

from .forms import ContactForm, JoinRequestForm, ResourceForm
from .models import ContactMessage, JoinRequest, Resource, ResourceCategory, User
from .services.weather import format_observed, get_metar

logger = logging.getLogger(__name__)


def _requested_year_month(request):
    today = timezone.localdate()
    month_param = request.GET.get("month")
    if month_param:
        try:
            # Unpacked here, inside the try - a generator expression is
            # lazy, so returning it unevaluated (as this used to do) let
            # a malformed value (e.g. "?month=banana") slip past this
            # except clause and blow up wherever the caller unpacked it
            # instead.
            year, month = (int(part) for part in month_param.split("-"))
            # int() alone accepts an out-of-range month (e.g. "13") or an
            # out-of-range year - date() is what actually validates both,
            # so constructing one here (and discarding it) is what makes
            # a value like "?month=9999-13" fall back too, instead of
            # crashing further down in get_month_calendar.
            date(year, month, 1)
            return year, month
        except (ValueError, OverflowError):
            # ValueError: not "int-int", or a year/month date() rejects
            # (e.g. month 13). OverflowError: a year so large it can't
            # even be tested against date()'s own range internally.
            pass
    return today.year, today.month


def home(request):
    year, month = _requested_year_month(request)
    return render(
        request,
        "app/home.html",
        {"calendar": get_month_calendar(request.organization, year, month)},
    )


def calendar_panel(request):
    # Backs the calendar's prev/next month navigation (see
    # static/js/home.js) - a fetch() swap of just this fragment, same
    # pattern as weather_panel, so switching months doesn't reload the
    # whole home page.
    year, month = _requested_year_month(request)
    return render(
        request,
        "app/components/calendar.html",
        {"calendar": get_month_calendar(request.organization, year, month)},
    )

def weather_panel(request):
    organization = request.organization
    metar = None
    observed_text = None
    if organization and organization.airport_icao:
        metar = get_metar(organization.airport_icao, org_name=organization.name)
        if metar:
            observed_text = format_observed(metar)

    return render(
        request,
        "app/components/weather_panel.html",
        {
            "metar": metar,
            "observed_text": observed_text,
        }
    )

def about(request):
    return render(request, "app/about.html")

def members(request):
    return under_construction(request,"Members")

def aircraft(request):
    return under_construction(request,"Aircraft")

def scholarship(request):
    application = None
    if request.organization:
        application = request.organization.resources.filter(
            title="Scholarship Application", is_enabled=True,
        ).first()

    return render(request, "app/scholarship.html", {"application": application})

def resources(request):
    organization = request.organization
    can_manage = request.user.has_perm("core.change_resource")
    categories = []

    if organization:
        # prefetch_related loads every category's resources in one extra
        # query total, rather than one query per category - then all
        # filtering below happens in Python against that already-fetched
        # list, so it doesn't cost a query of its own either.
        categories_qs = organization.enabled_resource_categories.prefetch_related("resources")
        for category in categories_qs:
            all_resources = category.resources.all()
            if can_manage:
                # Officers see disabled resources too (and can re-enable
                # them here) - everyone else only ever sees an enabled,
                # visible-to-them resource (visible_to() checks
                # is_enabled itself).
                visible = list(all_resources)
            else:
                visible = [r for r in all_resources if r.visible_to(request.user)]
            if visible:
                categories.append({"category": category, "resources": visible})

    return render(
        request, "app/resources.html",
        {"categories": categories, "can_manage": can_manage},
    )


@login_required
@permission_required("core.add_resource", raise_exception=True)
def resource_create(request):
    organization = request.organization
    if not organization:
        raise Http404

    if request.method == "POST":
        form = ResourceForm(request.POST, request.FILES, organization=organization)
        if form.is_valid():
            form.save()
            return redirect("core:resources")
    else:
        form = ResourceForm(organization=organization)

    return render(request, "app/resource_form.html", {"form": form})


@login_required
@permission_required("core.add_resourcecategory", raise_exception=True)
@require_POST
def resource_category_create(request):
    # Backs the "+ Add a new category" widget on resource_form.html - a
    # small fetch() call, not a full page (see static/js/resource_form.js),
    # so the category dropdown stays the one real answer to "which
    # category" instead of a second competing "or type a new one" field.
    #
    # Returns a rendered <option> fragment rather than JSON, matching
    # weather_panel's existing fetch()-for-an-HTML-fragment convention
    # (see home.js) instead of inventing a second response shape for
    # what's the same kind of interaction. format_html escapes the
    # title, since unlike a JSON response consumed via .textContent,
    # HTML built server-side has to escape untrusted input itself.
    organization = request.organization
    if not organization:
        raise Http404

    title = request.POST.get("title", "").strip()
    if not title:
        return HttpResponseBadRequest("Category name can't be blank.")

    category, _ = ResourceCategory.objects.get_or_create(
        organization=organization, title=title,
    )
    option_html = format_html(
        '<option value="{}" selected>{}</option>', category.pk, category.title,
    )
    return HttpResponse(option_html, status=201)


@login_required
@permission_required("core.change_resource", raise_exception=True)
@require_POST
def resource_toggle_enabled(request, slug):
    # Reversible, front-end - mirrors meeting_toggle_cancelled. A
    # permanent delete stays an /admin-only action, same reasoning as
    # meetings: this view only ever flips is_enabled, never deletes.
    resource = get_object_or_404(
        Resource, slug=slug, organization=request.organization,
    )
    resource.is_enabled = not resource.is_enabled
    resource.save(update_fields=["is_enabled"])
    return redirect("core:resources")


def resource_download(request, slug):
    # Visibility (public vs. members), not a permission, gates this -
    # any signed-in user can reach a "members" resource, matching how
    # the rest of the site treats a plain Member (see user-roles).
    resource = get_object_or_404(
        Resource, slug=slug, organization=request.organization, is_enabled=True,
    )
    if not resource.visible_to(request.user):
        return redirect_to_login(request.get_full_path())

    return FileResponse(
        resource.file.open("rb"),
        filename=Path(resource.file.name).name,
        as_attachment=False,
    )

def privacy_policy(request):
    return render(request, "app/privacy_policy.html")

def terms(request):
    return under_construction(request, "Terms of Use")

def contact(request):
    organization = request.organization
    if not organization:
        raise Http404

    if request.method == "POST":
        form = ContactForm(request.POST, organization=organization)
        if form.is_valid():
            contact_message = form.save()
            _notify_contact_message(contact_message)
            return redirect(f"{reverse('core:contact')}?sent=1")
    else:
        form = ContactForm(organization=organization)

    return render(
        request,
        "app/contact.html",
        {
            "form": form,
            "next_meeting": get_next_meeting(organization),
            "sent": request.GET.get("sent") == "1",
        },
    )


def _notify_contact_message(contact_message):
    # Best-effort - the message is already saved and visible in the admin
    # (see ContactMessage) regardless of whether this succeeds, so a
    # missing/misconfigured mail server (nothing is set up yet - see
    # EMAIL_BACKEND in settings) never loses a submission, just the
    # instant notification.
    organization = contact_message.organization
    if not organization.email:
        return

    try:
        send_mail(
            subject=f"New contact message from {contact_message.name}",
            message=(
                f"{contact_message.message}\n\n"
                f"— {contact_message.name} <{contact_message.email}>"
            ),
            from_email=None,
            recipient_list=[organization.email],
        )
    except Exception:
        logger.warning("Failed to send contact-message notification email", exc_info=True)

# Officer review pages - Messages (ContactMessage) and Applications
# (JoinRequest) share the SeenTracking pattern (see core/models.py): a
# list split into new/seen, plus separate mark-seen / mark-unseen
# actions rather than one toggle, so a page left open while another
# officer acts on the same item can't flip it back the wrong way.

def _review_list(request, related_name, template_name, *select_related):
    if not request.organization:
        raise Http404
    items = list(
        getattr(request.organization, related_name).select_related("seen_by", *select_related)
    )
    return render(
        request,
        template_name,
        {
            "unseen_items": [item for item in items if item.seen_at is None],
            "seen_items": [item for item in items if item.seen_at is not None],
        },
    )


def _review_item(request, model, pk):
    return get_object_or_404(model, pk=pk, organization=request.organization)


@login_required
@permission_required("core.view_contactmessage", raise_exception=True)
def contact_messages(request):
    return _review_list(request, "contact_messages", "app/contact_messages.html")


@login_required
@permission_required("core.change_contactmessage", raise_exception=True)
@require_POST
def contact_message_mark_seen(request, pk):
    _review_item(request, ContactMessage, pk).mark_seen(request.user)
    return redirect("core:contact_messages")


@login_required
@permission_required("core.change_contactmessage", raise_exception=True)
@require_POST
def contact_message_mark_unseen(request, pk):
    _review_item(request, ContactMessage, pk).mark_unseen()
    return redirect("core:contact_messages")


@login_required
@permission_required("core.delete_contactmessage", raise_exception=True)
@require_POST
def contact_message_delete(request, pk):
    _review_item(request, ContactMessage, pk).delete()
    return redirect("core:contact_messages")


@login_required
@permission_required("core.view_joinrequest", raise_exception=True)
def join_requests(request):
    # Not _review_list's plain new/seen split: pending applications are
    # split new/seen, and decided ones get their own Denied and Approved
    # sections (denied are kept so a mistake can still be approved).
    if not request.organization:
        raise Http404
    items = list(request.organization.join_requests.select_related("seen_by", "decided_by"))
    pending = [item for item in items if item.is_pending]
    return render(
        request,
        "app/join_requests.html",
        {
            "unseen_items": [item for item in pending if item.seen_at is None],
            "seen_items": [item for item in pending if item.seen_at is not None],
            "denied_items": [item for item in items if item.is_denied],
            "approved_items": [item for item in items if item.is_approved],
        },
    )


@login_required
@permission_required("core.change_joinrequest", raise_exception=True)
@require_POST
def join_request_mark_seen(request, pk):
    _review_item(request, JoinRequest, pk).mark_seen(request.user)
    return redirect("core:join_requests")


@login_required
@permission_required("core.change_joinrequest", raise_exception=True)
@require_POST
def join_request_mark_unseen(request, pk):
    _review_item(request, JoinRequest, pk).mark_unseen()
    return redirect("core:join_requests")


# Approve works on a pending or a denied application (a mistaken denial
# can be reversed); Deny only on a pending one. Anything else is a no-op,
# so a stale page can't overturn another officer's decision - e.g. a
# Deny clicked after someone else approved.

@login_required
@permission_required("core.change_joinrequest", raise_exception=True)
@require_POST
def join_request_approve(request, pk):
    join_request = _review_item(request, JoinRequest, pk)
    if not join_request.is_approved:
        join_request.decide(JoinRequest.STATUS_APPROVED, request.user)
    return redirect("core:join_requests")


@login_required
@permission_required("core.change_joinrequest", raise_exception=True)
@require_POST
def join_request_deny(request, pk):
    join_request = _review_item(request, JoinRequest, pk)
    if join_request.is_pending:
        join_request.decide(JoinRequest.STATUS_DENIED, request.user)
    return redirect("core:join_requests")


@login_required
@permission_required("core.delete_joinrequest", raise_exception=True)
@require_POST
def join_request_delete(request, pk):
    _review_item(request, JoinRequest, pk).delete_with_account()
    return redirect("core:join_requests")


@login_required
@permission_required("core.view_user", raise_exception=True)
def user_list(request):
    # Read-only for now - changes to an account are made in /admin.
    users = list(User.objects.prefetch_related("groups").select_related("join_request"))
    role_order = {"Superadmin": 0, "Officer": 1, "Staff": 2, "Member": 3}
    users.sort(key=lambda user: (role_order[user.role], user.display_name.lower()))
    return render(
        request,
        "app/user_list.html",
        {
            "users": users,
            "active_count": sum(user.is_active for user in users),
            "pending_count": sum(user.account_status == "Pending approval" for user in users),
        },
    )


def join(request):
    organization = request.organization
    if not organization:
        raise Http404

    if request.method == "POST":
        form = JoinRequestForm(request.POST, organization=organization)
        if form.is_valid():
            form.save()
            # Back to the form's own section, where the thank-you shows.
            return redirect(f"{reverse('core:join')}?sent=1#apply")
    else:
        form = JoinRequestForm(organization=organization)

    return render(
        request,
        "app/join.html",
        {
            "form": form,
            "next_meeting": get_next_meeting(organization),
            "sent": request.GET.get("sent") == "1",
        },
    )

def youngeagles(request):
    return render(request, "app/youngeagles.html")

def under_construction(request, page_title, page_description=None):
    """Render the generic "under construction" placeholder page.

    This is the reusable template for stubbing out a not-yet-built page:

        1. Add a view that just calls this helper, e.g.:
               def events(request):
                   return under_construction(
                       request, "Events", "Optional custom blurb here.",
                   )
           `page_description` is optional - omit it to fall back to the
           default copy used by the other stub pages.
        2. Wire it up in core/urls.py, e.g.:
               path("events", events, name="events"),

    That's it - no new template or view logic needed. When the real page
    is ready, replace the view body with the actual implementation and
    point its template at something other than app/construction.html.
    """
    return render(
        request,
        "app/construction.html",
        {
            "page_title": page_title,
            "page_description": page_description,
        },
    )