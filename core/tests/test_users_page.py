"""The officer Users page: listing, roles, deactivate/reactivate/unlock."""

from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import JoinRequest, User
from core.tests.base import SiteTestCase


class UsersPageTests(SiteTestCase):

    def setUp(self):
        self.officer = self.make_user("officer@example.com", role="officer")
        self.site_admin = self.make_user("sa@example.com", role="site_admin")
        self.member = self.make_user("member@example.com", first_name="Mem", last_name="Ber")
        self.root = self.make_user("root@example.com", role="superadmin")
        self.officer_client = self.client_for(self.officer)
        self.site_admin_client = self.client_for(self.site_admin)

    def row_for(self, html, email):
        start = html.find(f"mailto:{email}")
        return html[html.rfind("<tr", 0, start):html.find("</tr>", start)]

    def test_lists_every_account_with_role_and_status(self):
        self.apply("app@example.com")
        users = {u.email: u for u in self.officer_client.get("/users").context["users"]}
        self.assertEqual(set(users), {
            "officer@example.com", "sa@example.com", "member@example.com", "root@example.com", "app@example.com",
        })
        self.assertEqual(users["app@example.com"].role, "Applicant")
        self.assertEqual(users["app@example.com"].account_status, "Pending approval")
        self.assertEqual(users["member@example.com"].account_status, "Active")

    def test_sorted_by_role(self):
        roles = [u.role for u in self.officer_client.get("/users").context["users"]]
        self.assertEqual(roles, ["Superadmin", "Officer", "Site admin", "Member"])

    def test_query_count_doesnt_grow_with_users(self):
        self.officer_client.get("/users")
        with CaptureQueriesContext(connection) as before:
            self.officer_client.get("/users")
        for i in range(10):
            self.make_user(f"bulk{i}@example.com")
        with CaptureQueriesContext(connection) as after:
            self.officer_client.get("/users")
        self.assertEqual(len(before), len(after))

    # ---- roles ----

    def set_role(self, client, user, role):
        return client.post(f"/users/{user.pk}/role", {"role": role})

    def test_officer_changes_roles(self):
        for role, label in (("site_admin", "Site admin"), ("officer", "Officer"), ("member", "Member")):
            with self.subTest(role=role):
                self.set_role(self.officer_client, self.member, role)
                self.assertEqual(User.objects.get(pk=self.member.pk).role, label)

    def test_role_picker_shown_to_officers_only(self):
        officer_html = self.officer_client.get("/users").content.decode()
        self.assertIn('name="role"', self.row_for(officer_html, "member@example.com"))
        self.assertNotIn('name="role"', self.row_for(officer_html, "officer@example.com"))  # self
        self.assertNotIn('name="role"', self.row_for(officer_html, "root@example.com"))
        self.assertNotIn('name="role"', self.site_admin_client.get("/users").content.decode())

    def test_site_admin_cannot_change_roles(self):
        self.assertEqual(self.set_role(self.site_admin_client, self.member, "officer").status_code, 403)
        self.assertEqual(User.objects.get(pk=self.member.pk).role, "Member")

    def test_cannot_change_own_role(self):
        self.set_role(self.officer_client, self.officer, "member")
        self.assertEqual(User.objects.get(pk=self.officer.pk).role, "Officer")

    def test_officer_cannot_touch_superuser(self):
        self.assertEqual(self.set_role(self.officer_client, self.root, "member").status_code, 403)

    def test_applicant_role_cannot_be_changed(self):
        self.apply("app@example.com")
        applicant = User.objects.get(email="app@example.com")
        self.set_role(self.officer_client, applicant, "officer")
        self.assertEqual(User.objects.get(pk=applicant.pk).role, "Applicant")

    def test_bogus_role_ignored(self):
        for role in ("superadmin", "officer_site_admin", ""):
            self.set_role(self.officer_client, self.member, role)
        member = User.objects.get(pk=self.member.pk)
        self.assertEqual(member.role, "Member")
        self.assertFalse(member.is_superuser)

    def test_superadmin_can_change_roles(self):
        self.set_role(self.client_for(self.root), self.site_admin, "officer")
        self.assertEqual(User.objects.get(pk=self.site_admin.pk).role, "Officer")

    # ---- deactivate / reactivate ----

    def test_deactivate_and_reactivate(self):
        for client in (self.officer_client, self.site_admin_client):
            with self.subTest(client=client):
                client.post(f"/users/{self.member.pk}/deactivate")
                self.assertFalse(User.objects.get(pk=self.member.pk).is_active)
                self.assertEqual(User.objects.get(pk=self.member.pk).account_status, "Deactivated")
                client.post(f"/users/{self.member.pk}/reactivate")
                self.assertTrue(User.objects.get(pk=self.member.pk).is_active)

    def test_cannot_deactivate_self(self):
        self.officer_client.post(f"/users/{self.officer.pk}/deactivate")
        self.assertTrue(User.objects.get(pk=self.officer.pk).is_active)

    def test_cannot_deactivate_superuser(self):
        self.assertEqual(self.officer_client.post(f"/users/{self.root.pk}/deactivate").status_code, 403)
        self.assertTrue(User.objects.get(pk=self.root.pk).is_active)

    def test_cannot_reactivate_unapproved_applicant(self):
        self.apply("app@example.com")
        applicant = User.objects.get(email="app@example.com")
        self.officer_client.post(f"/users/{applicant.pk}/reactivate")
        self.assertFalse(User.objects.get(pk=applicant.pk).is_active)
        self.officer_client.post(f"/applications/{JoinRequest.objects.get().pk}/deny")
        self.officer_client.post(f"/users/{applicant.pk}/reactivate")
        self.assertFalse(User.objects.get(pk=applicant.pk).is_active)

    def test_member_refused(self):
        member_client = self.client_for(self.member)
        for action in ("deactivate", "reactivate", "unlock"):
            with self.subTest(action=action):
                self.assertEqual(member_client.post(f"/users/{self.officer.pk}/{action}").status_code, 403)

    def test_actions_require_post(self):
        for action in ("deactivate", "reactivate", "unlock", "role"):
            with self.subTest(action=action):
                self.assertEqual(self.officer_client.get(f"/users/{self.member.pk}/{action}").status_code, 405)

    # ---- lockouts ----

    def test_locked_out_badge_and_unlock(self):
        for _ in range(5):
            self.client.post("/login/", {"username": "member@example.com", "password": "wrong"})
        response = self.site_admin_client.get("/users")
        row = self.row_for(response.content.decode(), "member@example.com")
        self.assertIn("Locked out", row)
        self.assertIn(">Active<", row)  # locked out isn't the same as deactivated
        self.assertEqual(response.context["locked_count"], 1)
        self.site_admin_client.post(f"/users/{self.member.pk}/unlock")
        self.assertEqual(self.site_admin_client.get("/users").context["locked_count"], 0)

    # ---- adding accounts ----

    def add_user(self, client, **overrides):
        data = {
            "first_name": "New", "last_name": "Pilot", "email": "New@Example.com",
            "password1": "Fresh-password-456", "password2": "Fresh-password-456",
            **overrides,
        }
        return client.post("/users/add", data)

    def test_officer_and_site_admin_add_users(self):
        for i, client in enumerate((self.officer_client, self.site_admin_client)):
            with self.subTest(client=client):
                response = self.add_user(client, email=f"new{i}@example.com")
                self.assertRedirects(response, "/users", fetch_redirect_response=False)
                account = User.objects.get(email=f"new{i}@example.com")
                self.assertTrue(account.is_active)
                self.assertEqual(account.role, "Member")
                self.assertFalse(account.is_staff)
                self.assertTrue(self.client.login(username=f"new{i}@example.com", password="Fresh-password-456"))

    def test_email_stored_lowercase_and_duplicates_refused(self):
        self.add_user(self.officer_client)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        response = self.add_user(self.officer_client, email="NEW@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.filter(email="new@example.com").count(), 1)

    def test_add_user_validates_passwords_and_names(self):
        for overrides in (
            {"password2": "Something-else-789"},
            {"password1": "short", "password2": "short"},
            {"first_name": ""},
        ):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.add_user(self.officer_client, **overrides).status_code, 200)
                self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_add_user_cannot_grant_privileges(self):
        self.add_user(self.officer_client, is_superuser="on", is_staff="on", groups="1")
        account = User.objects.get(email="new@example.com")
        self.assertFalse(account.is_superuser)
        self.assertFalse(account.is_staff)
        self.assertFalse(account.groups.exists())

    def test_add_user_refused_without_permission(self):
        member_client = self.client_for(self.member)
        self.assertEqual(member_client.get("/users/add").status_code, 403)
        self.assertEqual(self.add_user(member_client).status_code, 403)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())
        self.assertRedirects(self.client.get("/users/add"), "/login/?next=/users/add", fetch_redirect_response=False)

    def test_add_user_page_renders(self):
        self.assertContains(self.officer_client.get("/users/add"), "Create User")

    def test_add_button_shown_with_permission(self):
        self.assertIn('href="/users/add"', self.site_admin_client.get("/users").content.decode())
