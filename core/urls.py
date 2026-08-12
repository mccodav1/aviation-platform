from django.urls import path

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
    path("meetings", meetings, name="meetings"),
    path("youngeagles", youngeagles, name="youngeagles"),
    path("weather", weather_panel, name="weather_panel"),
    path("", home, name="home"),
]