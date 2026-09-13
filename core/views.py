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
    return under_construction(request,"Scholarship")

def resources(request):
    return under_construction(request,"Resources")

def contact(request):
    return under_construction(request,"Contact")

def join(request):
    return under_construction(request,"Join")

def youngeagles(request):
    return under_construction(request,"Young Eagles")

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
    return render(
        request,
        "app/construction.html",
        {
            "page_title": page_title,
            "page_description": page_description,
        },
    )