"""Messages from officers/site admins to members' Inboxes."""

from core.models import ContactMessage, MemberMessage, MemberMessageDelivery, User
from core.tests.base import SiteTestCase


class MemberMessageTests(SiteTestCase):

    def setUp(self):
        self.officer = self.make_user("officer@example.com", role="officer", first_name="Olivia", last_name="Officer")
        self.site_admin = self.make_user("sa@example.com", role="site_admin")
        self.member = self.make_user("member@example.com", first_name="Mel", last_name="Member")
        self.other = self.make_user("other@example.com")
        self.officer_client = self.client_for(self.officer)
        self.member_client = self.client_for(self.member)

    def send(self, client, to, subject="Hangar party", body="Saturday at noon."):
        return client.post("/inbox/compose", {"to": to, "subject": subject, "body": body})

    # ---- sending ----

    def test_officer_and_site_admin_send_to_one_person(self):
        for client in (self.officer_client, self.client_for(self.site_admin)):
            with self.subTest(client=client):
                response = self.send(client, self.member.pk)
                self.assertRedirects(response, "/inbox/sent?sent=1", fetch_redirect_response=False)
        self.assertEqual(MemberMessageDelivery.objects.filter(recipient=self.member).count(), 2)
        self.assertFalse(MemberMessageDelivery.objects.exclude(recipient=self.member).exists())

    def test_send_to_everyone_reaches_every_active_account_but_the_sender(self):
        self.apply("applicant@example.com")  # inactive until approved
        self.send(self.officer_client, "everyone")
        message = MemberMessage.objects.get()
        self.assertTrue(message.sent_to_everyone)
        self.assertEqual(
            set(message.deliveries.values_list("recipient__email", flat=True)),
            {"sa@example.com", "member@example.com", "other@example.com"},
        )

    def test_members_cannot_send(self):
        self.assertEqual(self.member_client.get("/inbox/compose").status_code, 403)
        self.assertEqual(self.send(self.member_client, "everyone").status_code, 403)
        self.assertFalse(MemberMessage.objects.exists())

    def test_cannot_send_to_inactive_or_unknown_accounts(self):
        self.apply("applicant@example.com")
        applicant = User.objects.get(email="applicant@example.com")
        for to in (applicant.pk, 99999, ""):
            with self.subTest(to=to):
                self.assertEqual(self.send(self.officer_client, to).status_code, 200)
        self.assertFalse(MemberMessage.objects.exists())

    def test_compose_prefills_recipient(self):
        form = self.officer_client.get(f"/inbox/compose?to={self.member.pk}").context["form"]
        self.assertEqual(form["to"].value(), str(self.member.pk))

    # ---- the inbox ----

    def test_inbox_shows_messages_then_marks_them_read(self):
        self.send(self.officer_client, self.member.pk, subject="Welcome!", body="Glad to have you.")
        self.assertContains(self.member_client.get("/"), 'class="nav-account-badge"')
        response = self.member_client.get("/inbox")
        self.assertEqual(len(response.context["new_items"]), 1)
        self.assertContains(response, "Welcome!")
        self.assertContains(response, "from Olivia Officer")
        self.assertIsNotNone(MemberMessageDelivery.objects.get().read_at)
        self.assertEqual(len(self.member_client.get("/inbox").context["read_items"]), 1)
        self.assertNotContains(self.member_client.get("/"), 'class="nav-account-badge"')

    def test_inbox_only_shows_your_own_messages(self):
        self.send(self.officer_client, self.other.pk, subject="Just for other")
        self.assertNotContains(self.member_client.get("/inbox"), "Just for other")

    def test_delete_hides_only_your_copy(self):
        self.send(self.officer_client, "everyone", subject="Fly-in")
        mine = MemberMessageDelivery.objects.get(recipient=self.member)
        theirs = MemberMessageDelivery.objects.get(recipient=self.other)
        self.assertEqual(self.member_client.post(f"/inbox/{theirs.pk}/delete").status_code, 404)
        self.member_client.post(f"/inbox/{mine.pk}/delete")
        self.assertNotContains(self.member_client.get("/inbox"), "Fly-in")
        self.assertContains(self.client_for(self.other).get("/inbox"), "Fly-in")

    def test_deleted_unread_message_stops_counting_as_unread(self):
        self.send(self.officer_client, self.member.pk)
        self.member_client.post(f"/inbox/{MemberMessageDelivery.objects.get().pk}/delete")
        self.assertNotContains(self.member_client.get("/"), 'class="nav-account-badge"')

    def test_sent_log_still_names_recipient_after_they_delete_it(self):
        # The reported bug: it said "to a deleted account".
        self.send(self.officer_client, self.member.pk, subject="To Mel")
        self.member_client.get("/inbox")
        self.member_client.post(f"/inbox/{MemberMessageDelivery.objects.get().pk}/delete")
        html = self.officer_client.get("/inbox/sent").content.decode()
        self.assertIn("to Mel Member", html)
        self.assertNotIn("deleted account", html)
        self.assertIn("Read by 1 of 1", html)

    def test_inbox_requires_login(self):
        self.assertRedirectsToLogin(self.client.get("/inbox"))

    # ---- sent log ----

    def test_sent_log_shows_recipients_and_read_counts(self):
        self.send(self.officer_client, "everyone", subject="To all")
        self.send(self.officer_client, self.member.pk, subject="To Mel")
        self.member_client.get("/inbox")
        html = self.client_for(self.site_admin).get("/inbox/sent").content.decode()
        self.assertIn("to everyone", html)
        self.assertIn("to Mel Member", html)
        self.assertIn("Read by 1 of 3", html)
        self.assertIn("Read by 1 of 1", html)
        self.assertEqual(self.member_client.get("/inbox/sent").status_code, 403)

    # ---- entry points ----

    def test_users_page_message_button(self):
        html = self.officer_client.get("/users").content.decode()
        self.assertIn(f'href="/inbox/compose?to={self.member.pk}"', html)
        self.assertNotIn(f'href="/inbox/compose?to={self.officer.pk}"', html)  # not yourself

    def test_reply_to_contact_message_from_a_member(self):
        from_member = ContactMessage.objects.create(organization=self.org, name="Mel", email="Member@Example.com", message="Is the\nmeeting on?")
        from_stranger = ContactMessage.objects.create(organization=self.org, name="Stranger", email="who@example.com", message="Hi")
        html = self.officer_client.get("/messages").content.decode()
        self.assertIn(f"?to={self.member.pk}&amp;reply={from_member.pk}", html)
        self.assertNotIn(f"reply={from_stranger.pk}", html)

        form = self.officer_client.get(f"/inbox/compose?to={self.member.pk}&reply={from_member.pk}").context["form"]
        self.assertEqual(form["subject"].value(), "Re: your message")
        self.assertIn("> Is the\n> meeting on?", form["body"].value())


class MemberMessageCleanupTests(SiteTestCase):
    """Deleting from the Sent log, and erasing once nobody has it."""

    setUp = MemberMessageTests.setUp
    send = MemberMessageTests.send

    def delete_from_sent(self, client, message):
        return client.post(f"/inbox/sent/{message.pk}/delete")

    def hide(self, user):
        delivery = MemberMessageDelivery.objects.get(recipient=user)
        return self.client_for(user).post(f"/inbox/{delivery.pk}/delete")

    def test_sent_log_delete_hides_it_for_every_sender_but_recipients_keep_it(self):
        self.send(self.officer_client, self.member.pk, subject="Hello Mel")
        self.delete_from_sent(self.client_for(self.site_admin), MemberMessage.objects.get())
        self.assertNotContains(self.officer_client.get("/inbox/sent"), "Hello Mel")
        self.assertContains(self.member_client.get("/inbox"), "Hello Mel")
        self.assertTrue(MemberMessage.objects.exists())

    def test_erased_once_off_sent_log_and_recipient_deleted_it_either_order(self):
        for sender_first in (True, False):
            with self.subTest(sender_first=sender_first):
                self.send(self.officer_client, self.member.pk)
                message = MemberMessage.objects.get()
                if sender_first:
                    self.delete_from_sent(self.officer_client, message)
                    self.assertTrue(MemberMessage.objects.exists())
                    self.hide(self.member)
                else:
                    self.hide(self.member)
                    self.assertTrue(MemberMessage.objects.exists())
                    self.delete_from_sent(self.officer_client, message)
                self.assertFalse(MemberMessage.objects.exists())
                self.assertFalse(MemberMessageDelivery.objects.exists())

    def test_everyone_message_waits_for_every_active_recipient(self):
        self.send(self.officer_client, "everyone")
        message = MemberMessage.objects.get()
        self.delete_from_sent(self.officer_client, message)
        self.hide(self.member)
        self.hide(self.site_admin)
        self.assertTrue(MemberMessage.objects.exists())  # self.other still has it
        # ...until they're deactivated - they can't log in to delete it.
        self.officer_client.post(f"/users/{self.other.pk}/deactivate")
        self.assertFalse(MemberMessage.objects.exists())

    def test_members_cannot_delete_from_sent_log(self):
        self.send(self.officer_client, self.member.pk)
        self.assertEqual(self.delete_from_sent(self.member_client, MemberMessage.objects.get()).status_code, 403)
        self.assertIsNone(MemberMessage.objects.get().removed_from_sent_at)
