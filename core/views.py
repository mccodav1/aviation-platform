from django.shortcuts import render
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
    return render(request, "app/scholarship.html")

def resources(request):
    return under_construction(request,"Resources")

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