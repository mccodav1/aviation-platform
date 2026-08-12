from core.services.weather import get_metar
from django.shortcuts import render

from core.models import HeroImage

def home(request):
    return render(
        request,
        "app/home.html",
        {
            "metar": get_metar("KSNS")
        }
    )

def about(request):
    return under_construction(request,"About")

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

def meetings(request):
    return under_construction(request,"Meetings")

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