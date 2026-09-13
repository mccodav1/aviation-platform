from django.urls import path

# Tied to the "meetings" app being installed (see settings.py) - if that
# app is ever removed for a deployment, drop these routes too.
from meetings.views import (
    meeting_agenda_download,
    meeting_agenda_manage,
    meeting_create,
    meeting_detail,
    meeting_ics,
    meeting_list,
    meeting_minutes_download,
    meeting_minutes_manage,
    meeting_toggle_cancelled,
    meetings_ics_feed,
)

from .views import *

app_name = "core"

urlpatterns = [
    path("about", about, name="about"),
    path("aircraft", aircraft, name="aircraft"),
    path("members", members, name="members"),
    path("scholarship", scholarship, name="scholarship"),
    path("resources", resources, name="resources"),
    path("resources/add", resource_create, name="resource_create"),
    path("resources/categories/add", resource_category_create, name="resource_category_create"),
    path("resources/<slug:slug>/download", resource_download, name="resource_download"),
    path("contact", contact, name="contact"),
    path("join", join, name="join"),
    path("meetings", meeting_list, name="meetings"),
    path("meetings/feed.ics", meetings_ics_feed, name="meetings_ics_feed"),
    path("meetings/add", meeting_create, name="meeting_create"),
    path("meetings/<int:pk>", meeting_detail, name="meeting_detail"),
    path("meetings/<int:pk>/ics", meeting_ics, name="meeting_ics"),
    path("meetings/<int:pk>/cancel", meeting_toggle_cancelled, name="meeting_toggle_cancelled"),
    path("meetings/<int:pk>/agenda", meeting_agenda_manage, name="meeting_agenda_manage"),
    path("meetings/<int:pk>/agenda/download", meeting_agenda_download, name="meeting_agenda_download"),
    path("meetings/<int:pk>/minutes", meeting_minutes_manage, name="meeting_minutes_manage"),
    path("meetings/<int:pk>/minutes/download", meeting_minutes_download, name="meeting_minutes_download"),
    path("youngeagles", youngeagles, name="youngeagles"),
    path("events", events, name="events"),
    path("weather", weather_panel, name="weather_panel"),
    path("", home, name="home"),
]