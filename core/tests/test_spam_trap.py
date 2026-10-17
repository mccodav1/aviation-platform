"""The honeypot on the public Join and Contact forms (HoneypotMixin)."""

from django.test import Client

from core.models import ContactMessage, JoinRequest, User
from core.tests.base import SiteTestCase


class SpamTrapTests(SiteTestCase):

    def contact(self, **extra):
        data = {"name": "Pat", "email": "pat@example.com", "message": "Hello", **extra}
        return Client().post("/contact", data)

    def test_trap_rendered_hidden_on_both_forms(self):
        for url in ("/join", "/contact"):
            with self.subTest(url=url):
                html = Client().get(url).content.decode()
                self.assertIn('class="form-field-trap" aria-hidden="true"', html)
                self.assertIn('name="website"', html)
                self.assertIn('tabindex="-1"', html)

    def test_filled_trap_drops_application_but_looks_sent(self):
        response = self.apply("bot@example.com", website="http://spam.example")
        self.assertRedirects(response, "/join?sent=1#apply", fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(email="bot@example.com").exists())
        self.assertFalse(JoinRequest.objects.exists())

    def test_filled_trap_drops_contact_message_but_looks_sent(self):
        response = self.contact(website="http://spam.example")
        self.assertRedirects(response, "/contact?sent=1", fetch_redirect_response=False)
        self.assertFalse(ContactMessage.objects.exists())

    def test_empty_trap_lets_real_submissions_through(self):
        self.apply("real@example.com", website="")
        self.contact(website="   ")
        self.assertTrue(JoinRequest.objects.filter(email="real@example.com").exists())
        self.assertTrue(ContactMessage.objects.exists())
