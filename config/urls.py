import re

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('django.contrib.auth.urls')),
    path('', include("core.urls")),
]

# Public media for `make runserver`. Under compose, nginx serves /media/
# straight off the media volume and this route is never reached.
# Deliberately not django.conf.urls.static.static(), which no-ops when
# DEBUG is off. private_media/ has no route at all - see core/storage.py.
urlpatterns += [
    re_path(
        r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")),
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
