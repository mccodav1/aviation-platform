"""Every public page renders, and the officer-only navbar icons stay
hidden from people who can't use them."""

from unittest import mock

from core.tests.base import SiteTestCase


class PublicPageTests(SiteTestCase):

    PUBLIC_PAGES = [
        "/", "/about", "/events", "/meetings", "/resources", "/scholarship",
        "/youngeagles", "/contact", "/join", "/privacy", "/terms", "/members",
        "/aircraft", "/login/", "/calendar",
    ]

    def test_public_pages_render(self):
        for url in self.PUBLIC_PAGES:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_unknown_page_is_404(self):
        self.assertEqual(self.client.get("/no-such-page").status_code, 404)

    def test_calendar_month_param(self):
        response = self.client.get("/calendar?month=2027-02")
        self.assertContains(response, "February 2027")

    def test_calendar_bad_month_falls_back_instead_of_crashing(self):
        for value in ("banana", "2027-13", "9999999-01", "2027", ""):
            with self.subTest(month=value):
                self.assertEqual(self.client.get(f"/calendar?month={value}").status_code, 200)

    def test_home_shows_join_button_to_visitors(self):
        self.org.join_url = "core:join"
        self.org.join_button_text = "Join Today"
        self.org.save()
        self.assertContains(self.client.get("/"), "Join Today")

    def test_contact_page_shows_airport_address(self):
        self.assertContains(self.client.get("/contact"), "30 Mortensen Avenue, Salinas, CA 93905")

    def test_weather_panel_without_network(self):
        with mock.patch("core.views.get_metar", return_value=None) as get_metar:
            response = self.client.get("/weather")
        self.assertEqual(response.status_code, 200)
        get_metar.assert_called_once()

    def test_media_route_serves_public_uploads(self):
        # The fallback route for `make runserver` (nginx serves /media/
        # under compose) - a missing file is a clean 404.
        self.assertEqual(self.client.get("/media/does-not-exist.png").status_code, 404)


class NavbarIconTests(SiteTestCase):
    """Users/Applications/Messages icons follow the permission ladder."""

    def icons(self, user=None):
        html = self.client_for(user).get("/about").content.decode()
        return {name: f'href="/{name}"' in html for name in ("users", "applications", "messages")}

    def test_visitor_and_member_see_no_officer_icons(self):
        self.assertEqual(self.icons(), {"users": False, "applications": False, "messages": False})
        member = self.make_user("member@example.com")
        self.assertEqual(self.icons(member), {"users": False, "applications": False, "messages": False})

    def test_site_admin_sees_users_only(self):
        site_admin = self.make_user("sa@example.com", role="site_admin")
        self.assertEqual(self.icons(site_admin), {"users": True, "applications": False, "messages": False})

    def test_officer_and_superadmin_see_all(self):
        for role in ("officer", "superadmin"):
            with self.subTest(role=role):
                user = self.make_user(f"{role}@example.com", role=role)
                self.assertEqual(self.icons(user), {"users": True, "applications": True, "messages": True})

    def test_logged_in_user_sees_log_out_not_join(self):
        html = self.client_for(self.make_user("m@example.com")).get("/about").content.decode()
        self.assertIn("Log Out", html)
        self.assertNotIn('class="login-button"', html)


class BetaTouchesTests(SiteTestCase):
    """The Report Bug button, the Contact page's bug-report section, and
    the login page's forgotten-password note."""

    BUG_URL = "/contact?topic=bug#message-form"

    def test_report_bug_button_on_every_page(self):
        member = self.client_for(self.make_user("m@example.com"))
        for client in (self.client, member):
            for url in ("/", "/about", "/contact", "/login/"):
                with self.subTest(url=url, logged_in=client is member):
                    self.assertContains(client.get(url), f'class="nav-bug-button" href="{self.BUG_URL}"')

    def test_bug_report_starts_message_with_template(self):
        response = self.client.get("/contact?topic=bug")
        self.assertTrue(response.context["reporting_bug"])
        self.assertIn("What happened instead:", response.context["form"]["message"].value())
        self.assertRegex(response.content.decode(), r'class="contact-tab active"\s+aria-current="page">\s+<i class="bi bi-bug"')

    def test_plain_contact_page_starts_empty_with_both_tabs(self):
        response = self.client.get("/contact")
        self.assertFalse(response.context["reporting_bug"])
        self.assertIsNone(response.context["form"]["message"].value())
        html = response.content.decode()
        self.assertIn('href="/contact#message-form"', html)  # back to a plain message
        self.assertIn(f'href="{self.BUG_URL}"', html)
        self.assertRegex(html, r'class="contact-tab active"\s+aria-current="page">\s+<i class="bi bi-chat-text"')

    def test_login_page_says_to_contact_an_officer(self):
        self.assertContains(self.client.get("/login/"), 'Forgot your password? <a href="/contact">Contact an officer</a>')
