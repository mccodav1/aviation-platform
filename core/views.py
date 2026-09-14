from pathlib import Path

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import redirect_to_login
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html
from django.views.decorators.http import require_POST

from .forms import ResourceForm
from .models import Resource, ResourceCategory
from .services.weather import get_metar


def home(request):
    return render(request,"app/home.html")

def weather_panel(request):
    organization = request.organization
    metar = None
    if organization and organization.airport_icao:
        metar = get_metar(organization.airport_icao)

    return render(
        request,
        "app/components/weather_panel.html",
        {
            "metar": metar,
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

def contact(request):
    return under_construction(request,"Contact")

def join(request):
    return under_construction(request,"Join")

def youngeagles(request):
    return render(request, "app/youngeagles.html")

def events(request):
    return under_construction(
        request,
        "Events",
        "We're working on a full calendar of fly-outs, socials, and club "
        "events. Check back soon.",
    )

# Create your views here.
# def home(request):
#     return render(request, "home.html")
# #
# # def base_app(request):
# #     return render(request, "app/base_app.html")
# #
# # def dashboard(request):
# #     return render(request, "app/dashboard.html")


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