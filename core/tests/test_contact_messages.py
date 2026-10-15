"""Contact page submissions and the officer Messages page."""

from unittest import mock

from django.core import mail

from core.models import ContactMessage
from core.tests.base import SiteTestCase


class ContactFormTests(SiteTestCase):

    def submit(self, **extra):
        data = {"name": "Cara", "email": "cara@example.com", "message": "Hello there", **extra}
        return self.client.post("/contact", data)

    def test_message_saved(self):
        response = self.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.get().organization, self.org)
        self.assertContains(self.client.get("/contact?sent=1"), "Thanks for reaching out")

    def test_notification_emailed_to_the_club(self):
        self.submit()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["info@example.com"])

    def test_saved_even_if_email_fails(self):
        with mock.patch("core.views.send_mail", side_effect=OSError("no mail server")):
            response = self.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_invalid_submission(self):
        self.assertEqual(self.submit(email="not-an-email").status_code, 200)
        self.assertFalse(ContactMessage.objects.exists())


class MessagesPageTests(SiteTestCase):

    def setUp(self):
        self.officer = self.make_user("officer@example.com", role="officer", first_name="Jim", last_name="S")
        self.officer_client = self.client_for(self.officer)
        self.message = ContactMessage.objects.create(
            organization=self.org, name="Cara <b>bold</b>", email="c@example.com", message="Line one\nLine two",
        )

    def test_page_lists_new_messages_escaped(self):
        response = self.officer_client.get("/messages")
        self.assertContains(response, "Cara &lt;b&gt;bold&lt;/b&gt;")
        self.assertContains(response, "Line one<br>Line two")
        self.assertEqual(list(response.context["unseen_items"]), [self.message])

    def test_seen_is_shared_and_shows_who(self):
        other_officer = self.client_for(self.make_user("other@example.com", role="officer"))
        self.officer_client.post(f"/messages/{self.message.pk}/seen")
        response = other_officer.get("/messages")
        self.assertEqual(list(response.context["seen_items"]), [self.message])
        self.assertContains(response, "Seen by Jim S")
        self.assertEqual(other_officer.get("/about").context["unseen_contact_message_count"], 0)

    def test_mark_unseen(self):
        self.officer_client.post(f"/messages/{self.message.pk}/seen")
        self.officer_client.post(f"/messages/{self.message.pk}/unseen")
        self.message.refresh_from_db()
        self.assertIsNone(self.message.seen_at)
        self.assertIsNone(self.message.seen_by)

    def test_delete(self):
        self.officer_client.post(f"/messages/{self.message.pk}/delete")
        self.assertFalse(ContactMessage.objects.exists())

    def test_badge_count(self):
        ContactMessage.objects.create(organization=self.org, name="B", email="b@example.com", message="x")
        self.assertEqual(self.officer_client.get("/about").context["unseen_contact_message_count"], 2)

    def test_site_admin_and_member_refused(self):
        for role in ("site_admin", "member"):
            client = self.client_for(self.make_user(f"{role}@example.com", role=role))
            with self.subTest(role=role):
                self.assertEqual(client.get("/messages").status_code, 403)
                self.assertEqual(client.post(f"/messages/{self.message.pk}/delete").status_code, 403)
        self.assertTrue(ContactMessage.objects.exists())

    def test_actions_require_post(self):
        for action in ("seen", "unseen", "delete"):
            with self.subTest(action=action):
                self.assertEqual(self.officer_client.get(f"/messages/{self.message.pk}/{action}").status_code, 405)
