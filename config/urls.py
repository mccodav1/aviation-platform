import re

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.static import serve

from core.forms import EmailAuthenticationForm

# Account URLs - django.contrib.auth.urls, listed out by hand instead of
# include()d, so the password-reset pages can be left out.
#
# PASSWORD RESET IS OFF until the site can send email (no EMAIL_* settings
# exist yet - see "Email: not set up yet" in docs/DEPLOY.md). Without a
# mail server, /password_reset/ would tell people "we've emailed you" when
# nothing was sent. Until then, an officer or site admin resets a
# forgotten password in /admin -> Users. To turn it back on, configure
# email and add these four routes (Django's own views and default
# templates; the login page could then link to password_reset):
#
#   path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
#   path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
#   path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
#   path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
account_urlpatterns = [
    # The email login form (see core/forms.py), with login throttling.
    path('login/', auth_views.LoginView.as_view(authentication_form=EmailAuthenticationForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # A logged-in user changing their own password - works without email.
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    *account_urlpatterns,
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
