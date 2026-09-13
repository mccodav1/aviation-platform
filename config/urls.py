"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
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

# Unlike static/ (handled by WhiteNoise, see settings.py), media/ is
# runtime-uploaded content with no build-time collection step, so it still
# needs an explicit serving route - not just a DEBUG-only dev convenience.
# Deliberately NOT using django.conf.urls.static.static() here: that
# helper silently no-ops whenever DEBUG is False, which is exactly the gap
# that broke media in production. Fine for this project's scale to have
# Django serve media directly; swap in a real web server in front of the
# media/ volume later if traffic ever makes that worth it. private_media/
# deliberately has no route here at all - see meetings/storage.py.
urlpatterns += [
    re_path(
        r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")),
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
