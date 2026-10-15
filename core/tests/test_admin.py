"""Django's admin: officers and site admins can manage accounts there
without being able to escalate, and private files don't crash it."""

from django.contrib.auth.models import Group

from core.models import ContactMessage, JoinRequest, User
from core.permissions import OFFICER_GROUP_NAME
from core.tests.base import PASSWORD, SiteTestCase


class UserAdminTests(SiteTestCase):

    def setUp(self):
        self.officer = self.make_user("officer@example.com", role="officer")
        self.site_admin = self.make_user("sa@example.com", role="site_admin")
        self.member = self.make_user("member@example.com", first_name="Mem", last_name="Ber")
        self.root = self.make_user("root@example.com", role="superadmin")

    def change_url(self, user):
        return f"/admin/core/user/{user.pk}/change/"

    def post_change(self, client, user, **overrides):
        data = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined_0": "2026-01-01",
            "date_joined_1": "12:00:00",
            "_save": "Save",
        }
        if user.is_active:
            data["is_active"] = "on"
        if user.is_staff:
            data["is_staff"] = "on"
        data["groups"] = [g.pk for g in user.groups.all()]
        data.update(overrides)
        return client.post(self.change_url(user), {k: v for k, v in data.items() if v not in ("", None)})

    def test_superuser_checkbox_hidden_from_non_superusers(self):
        for user in (self.officer, self.site_admin):
            html = self.client_for(user).get(self.change_url(self.member)).content.decode()
            with self.subTest(user=user.email):
                self.assertNotIn('name="is_superuser"', html)
                self.assertNotIn('name="user_permissions"', html)
        self.assertIn('name="is_superuser"', self.client_for(self.root).get(self.change_url(self.member)).content.decode())

    def test_cannot_escalate_via_post(self):
        for user in (self.officer, self.site_admin):
            with self.subTest(user=user.email):
                self.post_change(self.client_for(user), self.member, is_superuser="on")
                self.post_change(self.client_for(user), user, is_superuser="on")
                self.assertFalse(User.objects.get(pk=self.member.pk).is_superuser)
                self.assertFalse(User.objects.get(pk=user.pk).is_superuser)

    def test_officer_groups_limited_to_role_groups(self):
        other = Group.objects.create(name="Secret Powers")
        self.post_change(self.client_for(self.officer), self.member, groups=[other.pk])
        self.assertFalse(User.objects.get(pk=self.member.pk).groups.filter(name="Secret Powers").exists())

    def test_site_admin_cannot_assign_roles_in_admin(self):
        html = self.client_for(self.site_admin).get(self.change_url(self.member)).content.decode()
        self.assertNotIn('name="groups"', html)
        self.assertNotIn('name="is_staff"', html)
        officers = Group.objects.get(name=OFFICER_GROUP_NAME)
        self.post_change(self.client_for(self.site_admin), self.member, groups=[officers.pk], is_staff="on")
        member = User.objects.get(pk=self.member.pk)
        self.assertEqual(member.role, "Member")
        self.assertFalse(member.is_staff)

    def test_superuser_account_is_read_only_to_others(self):
        client = self.client_for(self.officer)
        self.assertNotIn('name="_save"', client.get(self.change_url(self.root)).content.decode())
        self.assertEqual(self.post_change(client, self.root, email="pwned@example.com").status_code, 403)
        self.assertEqual(client.get(f"/admin/core/user/{self.root.pk}/password/").status_code, 403)
        self.assertEqual(User.objects.get(pk=self.root.pk).email, "root@example.com")

    def test_password_reset_of_member_allowed(self):
        response = self.client_for(self.site_admin).post(f"/admin/core/user/{self.member.pk}/password/", {
            "password1": "Reset-pass-456", "password2": "Reset-pass-456", "usable_password": "true",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.get(pk=self.member.pk).check_password("Reset-pass-456"))

    def test_only_superusers_delete_users(self):
        response = self.client_for(self.officer).post(f"/admin/core/user/{self.member.pk}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.member.pk).exists())

    def test_admin_create_user_by_email(self):
        response = self.client_for(self.officer).post("/admin/core/user/add/", {
            "email": "New@Example.com", "usable_password": "true",
            "password1": "Another-pass-99", "password2": "Another-pass-99", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.get(email="new@example.com").check_password("Another-pass-99"))

    def test_activating_unapproved_applicant_refused(self):
        self.apply("app@example.com")
        applicant = User.objects.get(email="app@example.com")
        response = self.post_change(self.client_for(self.root), applicant, is_active="on")
        self.assertContains(response, "Approve it on the Applications page")
        self.assertFalse(User.objects.get(pk=applicant.pk).is_active)


class ReviewAdminTests(SiteTestCase):

    def setUp(self):
        self.officer_client = self.client_for(self.make_user("officer@example.com", role="officer"))

    def test_no_add_for_applications_or_messages(self):
        self.assertEqual(self.officer_client.get("/admin/core/joinrequest/add/").status_code, 403)
        self.assertEqual(self.officer_client.get("/admin/core/contactmessage/add/").status_code, 403)

    def test_admin_delete_application_matches_site(self):
        self.apply("pending@example.com")
        self.officer_client.post(f"/admin/core/joinrequest/{JoinRequest.objects.get().pk}/delete/", {"post": "yes"})
        self.assertFalse(User.objects.filter(email="pending@example.com").exists())

    def test_admin_bulk_delete_keeps_approved_members(self):
        self.apply("pending@example.com")
        self.apply("approved@example.com")
        approved = JoinRequest.objects.get(email="approved@example.com")
        self.officer_client.post(f"/applications/{approved.pk}/approve")
        self.officer_client.post("/admin/core/joinrequest/", {
            "action": "delete_selected",
            "_selected_action": [jr.pk for jr in JoinRequest.objects.all()],
            "post": "yes",
        })
        self.assertFalse(JoinRequest.objects.exists())
        self.assertFalse(User.objects.filter(email="pending@example.com").exists())
        self.assertTrue(User.objects.filter(email="approved@example.com").exists())

    def test_message_and_application_pages_render(self):
        ContactMessage.objects.create(organization=self.org, name="A", email="a@example.com", message="x")
        self.apply("app@example.com")
        self.assertEqual(self.officer_client.get(
            f"/admin/core/contactmessage/{ContactMessage.objects.get().pk}/change/").status_code, 200)
        self.assertEqual(self.officer_client.get(
            f"/admin/core/joinrequest/{JoinRequest.objects.get().pk}/change/").status_code, 200)


class PrivateFileAdminTests(SiteTestCase):
    """Regression: the admin's edit page 500'd for anything with a private
    file, because its file widget asks storage for a URL."""

    def test_resource_and_event_with_files_render(self):
        from meetings.models import Event, EventAttachment

        client = self.client_for(self.make_user("root@example.com", role="superadmin"))
        resource = self.make_resource()
        event = Event.objects.create(
            organization=self.org, title="Meeting", starts_at="2027-01-01T18:00Z", location="x",
            agenda=self.upload("agenda.pdf"), minutes=self.upload("minutes.pdf"),
        )
        EventAttachment.objects.create(event=event, title="Report", file=self.upload("report.pdf"))
        self.assertEqual(client.get(f"/admin/core/resource/{resource.pk}/change/").status_code, 200)
        self.assertEqual(client.get(f"/admin/meetings/event/{event.pk}/change/").status_code, 200)


class AdminLoginTests(SiteTestCase):

    def test_member_cannot_use_admin(self):
        self.make_user("member@example.com")
        response = self.client.post("/admin/login/", {"username": "member@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)  # stays on the login form
        self.assertRedirectsToLogin(self.client.get("/admin/"))
