"""Smaller pieces: link fields, weather formatting, the visitor-timezone
middleware, and the management commands."""

from datetime import datetime, timedelta, timezone as dt_timezone
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone

from core.links import link_error, resolve_link
from core.middleware.timezone import BrowserTimezoneMiddleware
from core.models import NavigationItem, Officer, Organization, Resource
from core.services import weather
from core.tests.base import SiteTestCase


class LinkTests(SiteTestCase):

    def test_resolve(self):
        self.make_resource("Bylaws")
        self.assertEqual(resolve_link("core:events"), "/events")
        self.assertEqual(resolve_link("https://example.com/x"), "https://example.com/x")
        self.assertEqual(resolve_link("mailto:a@example.com"), "mailto:a@example.com")
        self.assertEqual(resolve_link("resource:bylaws"), "/resources/bylaws/download")
        self.assertEqual(resolve_link(""), "")

    def test_bad_links_degrade_instead_of_crashing(self):
        self.assertEqual(resolve_link("core:nope"), "core:nope")
        self.assertEqual(resolve_link("resource:missing"), "resource:missing")

    def test_link_error(self):
        self.make_resource("Bylaws")
        for good in ("core:events", "https://example.com", "tel:5551234", "resource:bylaws", ""):
            with self.subTest(good=good):
                self.assertIsNone(link_error(good))
        for bad in ("core:nope", "/events", "resource:missing"):
            with self.subTest(bad=bad):
                self.assertIsNotNone(link_error(bad))

    def test_disabled_resource_link_is_an_error(self):
        self.make_resource("Bylaws", is_enabled=False)
        self.assertIsNotNone(link_error("resource:bylaws"))


class WeatherFormattingTests(SiteTestCase):

    def test_wind(self):
        self.assertEqual(weather.format_wind({"wspd": 0}), "Calm")
        self.assertEqual(weather.format_wind({"wspd": 8, "wdir": 90}), "090° at 8 kt")
        self.assertEqual(weather.format_wind({"wspd": 3, "wdir": "VRB"}), "Variable at 3 kt")
        self.assertEqual(weather.format_wind({"wspd": 8, "wdir": None}), "8 kt")
        self.assertEqual(weather.format_wind({"wspd": 8, "wdir": "???"}), "8 kt")
        self.assertEqual(weather.format_wind({"wspd": 12, "wdir": 270, "wgst": 20}), "270° at 12 kt (gusts 20 kt)")

    def test_altimeter_converts_hpa_to_inhg(self):
        self.assertEqual(weather.format_altimeter({"altim": 1017.4}), '30.04"')
        self.assertIsNone(weather.format_altimeter({}))

    def test_sky(self):
        self.assertEqual(weather.format_sky({}), "Clear")
        self.assertEqual(
            weather.format_sky({"clouds": [{"cover": "FEW", "base": 2500}, {"cover": "BKN", "base": 12000}]}),
            "FEW 2,500 ft, BKN 12,000 ft",
        )

    def test_observed(self):
        now = datetime.now(dt_timezone.utc)
        self.assertEqual(weather.format_observed({"obsTime": now.timestamp()}), "Just now")
        self.assertEqual(weather.format_observed({"obsTime": (now - timedelta(minutes=5)).timestamp()}), "5 min ago")
        self.assertEqual(weather.format_observed({"obsTime": (now - timedelta(hours=3)).timestamp()}), "3 hrs ago")


class TimezoneMiddlewareTests(SiteTestCase):

    def zone_for(self, cookie=None):
        seen = {}

        def view(request):
            seen["zone"] = timezone.get_current_timezone_name()
            return HttpResponse()

        request = RequestFactory().get("/")
        if cookie is not None:
            request.COOKIES["tz"] = cookie
        BrowserTimezoneMiddleware(view)(request)
        return seen["zone"]

    def test_uses_browser_zone_from_cookie(self):
        self.assertEqual(self.zone_for("America/New_York"), "America/New_York")

    def test_falls_back_without_or_with_bad_cookie(self):
        default = self.zone_for()
        self.assertEqual(self.zone_for("Not/AZone"), default)
        self.assertEqual(self.zone_for(""), default)


class BootstrapSiteTests(SiteTestCase):
    """The one-time seed (make compose-seed) - starts from no
    Organization, as on a fresh deployment."""

    def setUp(self):
        Organization.objects.all().delete()

    def test_seed_loads_content_and_files(self):
        call_command("bootstrap_site", stdout=StringIO())
        org = Organization.objects.get()
        self.assertEqual(org.name, "Salinas Pilots Association")
        self.assertEqual(
            list(Officer.objects.values_list("role", flat=True)),
            ["President", "Vice President", "Secretary", "Treasurer"],
        )
        application = Resource.objects.get(slug="scholarship-application")
        self.assertTrue(application.file.storage.exists(application.file.name))
        self.assertTrue(org.logo.storage.exists(org.logo.name))
        self.assertTrue(NavigationItem.objects.exists())
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_seed_refuses_to_overwrite(self):
        call_command("bootstrap_site", stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("bootstrap_site", stdout=StringIO())

    def test_seeded_links_all_resolve(self):
        call_command("bootstrap_site", stdout=StringIO())
        out = StringIO()
        call_command("check_links", stdout=out)
        self.assertIn("All links OK", out.getvalue())
