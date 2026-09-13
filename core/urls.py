from django.urls import path

# Tied to the "meetings" app being installed (see settings.py) - if that
# app is ever removed for a deployment, drop this route too.
from meetings.views import meeting_list

from .views import *

app_name = "core"

urlpatterns = [
    path("about", about, name="about"),
    path("aircraft", aircraft, name="aircraft"),
    path("members", members, name="members"),
    path("scholarship", scholarship, name="scholarship"),
    path("resources", resources, name="resources"),
    path("contact", contact, name="contact"),
    path("join", join, name="join"),
    path("meetings", meeting_list, name="meetings"),
    path("youngeagles", youngeagles, name="youngeagles"),
    path("weather", weather_panel, name="weather_panel"),
    path("", home, name="home"),
]