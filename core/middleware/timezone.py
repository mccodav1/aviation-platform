import zoneinfo

from django.utils import timezone

# Set by static/js/timezone.js from the browser's own
# Intl.DateTimeFormat().resolvedOptions().timeZone.
TIMEZONE_COOKIE = "tz"


class BrowserTimezoneMiddleware:
    """Activates the visitor's own browser timezone for the request, so
    every timezone-aware path (the |date filter, timezone.localtime(),
    localdate(), form datetime fields, the admin) both displays and
    interprets times in the zone the person is actually in. Storage is
    always UTC regardless (USE_TZ). Falls back to settings.TIME_ZONE
    when the cookie is missing or isn't a real IANA zone name."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.COOKIES.get(TIMEZONE_COOKIE)
        try:
            timezone.activate(zoneinfo.ZoneInfo(tzname)) if tzname else timezone.deactivate()
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            timezone.deactivate()

        return self.get_response(request)
