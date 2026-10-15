"""Joining: applying creates an inactive account; officers approve
(activate) or deny (stay inactive) it on /applications."""

from django.core import mail

from core.models import JoinRequest, User
from core.tests.base import PASSWORD, SiteTestCase


class ApplyTests(SiteTestCase):

    def test_apply_creates_inactive_account_and_application(self):
        response = self.apply("Pat@Example.com", first_name="Pat", last_name="Pilot", phone="555-1234")
        self.assertEqual(response.status_code, 302)
        self.assertIn("sent=1", response["Location"])
        user = User.objects.get(email="pat@example.com")
        join_request = JoinRequest.objects.get()
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertEqual(join_request.user, user)
        self.assertEqual(join_request.email, "pat@example.com")
        self.assertTrue(join_request.is_pending)
        self.assertEqual(user.get_full_name(), "Pat Pilot")
        self.assertTrue(user.check_password(PASSWORD))

    def test_thank_you_message(self):
        self.assertContains(self.client.get("/join?sent=1"), "Thanks for applying")

    def test_password_mismatch_rejected(self):
        response = self.apply("pat@example.com", password2="different-pass-1")
        self.assertContains(response, "match")
        self.assertFalse(User.objects.exists())

    def test_weak_password_rejected(self):
        response = self.apply("pat@example.com", password="pat", password2="pat")
        self.assertContains(response, "too short")
        self.assertFalse(User.objects.exists())

    def test_password_too_similar_to_email_rejected(self):
        self.apply("skyhawkpilot@example.com", password="skyhawkpilot", password2="skyhawkpilot")
        self.assertFalse(User.objects.exists())

    def test_duplicate_email_rejected_any_case(self):
        self.apply("pat@example.com")
        response = self.apply("PAT@example.com")
        self.assertContains(response, "already exists")
        self.assertEqual(JoinRequest.objects.count(), 1)

    def test_existing_member_email_rejected(self):
        self.make_user("member@example.com")
        self.assertContains(self.apply("member@example.com"), "already exists")

    def test_required_fields(self):
        response = self.client.post("/join", {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_instrument_rated_is_a_choice(self):
        self.apply("ifr@example.com", pilot_status="instrument")
        self.assertEqual(JoinRequest.objects.get().get_pilot_status_display(), "Instrument rated")


class ReviewTests(SiteTestCase):

    def setUp(self):
        self.officer = self.make_user("officer@example.com", role="officer", first_name="Oscar", last_name="O")
        self.officer_client = self.client_for(self.officer)
        self.apply("pat@example.com")
        self.join_request = JoinRequest.objects.get()

    def post(self, action, client=None, join_request=None):
        join_request = join_request or self.join_request
        return (client or self.officer_client).post(f"/applications/{join_request.pk}/{action}")

    def refresh(self):
        self.join_request.refresh_from_db()
        if self.join_request.user:
            self.join_request.user.refresh_from_db()

    def test_approve_activates_account(self):
        self.post("approve")
        self.refresh()
        self.assertTrue(self.join_request.is_approved)
        self.assertTrue(self.join_request.user.is_active)
        self.assertEqual(self.join_request.decided_by, self.officer)
        self.assertEqual(self.join_request.seen_by, self.officer)  # deciding marks it seen

    def test_approved_applicant_can_log_in(self):
        self.post("approve")
        response = self.client.post("/login/", {"username": "pat@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    def test_deny_keeps_account_inactive(self):
        self.post("deny")
        self.refresh()
        self.assertTrue(self.join_request.is_denied)
        self.assertFalse(self.join_request.user.is_active)

    def test_denied_can_still_be_approved(self):
        self.post("deny")
        self.post("approve")
        self.refresh()
        self.assertTrue(self.join_request.is_approved)
        self.assertTrue(self.join_request.user.is_active)

    def test_stale_deny_cannot_overturn_approval(self):
        self.post("approve")
        self.post("deny")
        self.refresh()
        self.assertTrue(self.join_request.is_approved)
        self.assertTrue(self.join_request.user.is_active)

    def test_seen_and_unseen(self):
        self.post("seen")
        self.refresh()
        self.assertEqual(self.join_request.seen_by, self.officer)
        self.post("unseen")
        self.refresh()
        self.assertIsNone(self.join_request.seen_at)
        self.assertTrue(self.join_request.is_pending)

    def test_seen_keeps_first_viewer(self):
        other = self.make_user("other@example.com", role="officer")
        self.post("seen")
        self.post("seen", client=self.client_for(other))
        self.refresh()
        self.assertEqual(self.join_request.seen_by, self.officer)

    def test_delete_pending_removes_its_account(self):
        self.post("delete")
        self.assertFalse(JoinRequest.objects.exists())
        self.assertFalse(User.objects.filter(email="pat@example.com").exists())

    def test_delete_denied_removes_its_account(self):
        self.post("deny")
        self.post("delete")
        self.assertFalse(User.objects.filter(email="pat@example.com").exists())

    def test_delete_approved_keeps_the_member(self):
        self.post("approve")
        self.post("delete")
        self.assertFalse(JoinRequest.objects.exists())
        self.assertTrue(User.objects.filter(email="pat@example.com").exists())

    def test_delete_approved_then_deactivated_keeps_the_member(self):
        # Regression: this used to delete the account (it checked is_active).
        self.post("approve")
        user = User.objects.get(email="pat@example.com")
        user.is_active = False
        user.save()
        self.post("delete")
        self.assertTrue(User.objects.filter(email="pat@example.com").exists())

    def test_actions_require_post(self):
        for action in ("approve", "deny", "seen", "unseen", "delete"):
            with self.subTest(action=action):
                self.assertEqual(
                    self.officer_client.get(f"/applications/{self.join_request.pk}/{action}").status_code, 405,
                )

    def test_site_admin_and_member_refused(self):
        for role in ("site_admin", "member"):
            client = self.client_for(self.make_user(f"{role}@example.com", role=role))
            for action in ("approve", "deny", "seen", "delete"):
                with self.subTest(role=role, action=action):
                    self.assertEqual(self.post(action, client=client).status_code, 403)
        self.refresh()
        self.assertTrue(self.join_request.is_pending)

    def test_page_sections(self):
        self.apply("seen@example.com")
        self.apply("denied@example.com")
        self.apply("approved@example.com")
        by_email = {jr.email: jr for jr in JoinRequest.objects.all()}
        self.post("seen", join_request=by_email["seen@example.com"])
        self.post("deny", join_request=by_email["denied@example.com"])
        self.post("approve", join_request=by_email["approved@example.com"])
        context = self.officer_client.get("/applications").context
        self.assertEqual([jr.email for jr in context["unseen_items"]], ["pat@example.com"])
        self.assertEqual([jr.email for jr in context["seen_items"]], ["seen@example.com"])
        self.assertEqual([jr.email for jr in context["denied_items"]], ["denied@example.com"])
        self.assertEqual([jr.email for jr in context["approved_items"]], ["approved@example.com"])

    def test_applicant_text_is_escaped(self):
        self.apply("x@example.com", first_name="<script>alert(1)</script>")
        html = self.officer_client.get("/applications").content.decode()
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_badge_counts_unseen_pending(self):
        self.apply("second@example.com")
        self.assertEqual(self.officer_client.get("/about").context["unseen_join_request_count"], 2)
        self.post("approve")
        self.assertEqual(self.officer_client.get("/about").context["unseen_join_request_count"], 1)

    def test_applicant_shows_as_applicant_on_users_page(self):
        self.assertEqual(User.objects.get(email="pat@example.com").role, "Applicant")
        self.post("approve")
        self.assertEqual(User.objects.get(email="pat@example.com").role, "Member")

    def test_no_email_sent_on_apply(self):
        # Nothing is emailed until email is set up - just a reminder that
        # applying works without a mail server.
        self.assertEqual(len(mail.outbox), 0)
