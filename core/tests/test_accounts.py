"""Email logins, the user model, the admin account command, and the
account URLs (password reset is deliberately off)."""

import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError

from core.models import User
from core.tests.base import PASSWORD, SiteTestCase


class UserModelTests(SiteTestCase):

    def test_email_is_stored_lowercase(self):
        user = self.make_user("  Pat@Example.COM ")
        self.assertEqual(user.email, "pat@example.com")

    def test_email_unique_regardless_of_case(self):
        self.make_user("pat@example.com")
        with self.assertRaises(IntegrityError):
            self.make_user("PAT@example.com")

    def test_email_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password=PASSWORD)

    def test_superuser_flags(self):
        user = self.make_user("root@example.com", role="superadmin")
        self.assertTrue(user.is_superuser and user.is_staff)

    def test_no_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertNotIn("username", [field.name for field in User._meta.get_fields()])

    def test_display_name(self):
        self.assertEqual(self.make_user("a@example.com", first_name="Ann", last_name="Lee").display_name, "Ann Lee")
        self.assertEqual(self.make_user("b@example.com").display_name, "b@example.com")


class LoginTests(SiteTestCase):

    def login(self, email, password=PASSWORD, **client_kwargs):
        return self.client_for(**client_kwargs).post("/login/", {"username": email, "password": password})

    def test_login_page_asks_for_email(self):
        self.assertContains(self.client.get("/login/"), "Email</label>")

    def test_login_by_email_any_case(self):
        self.make_user("pat@example.com")
        response = self.login("PAT@Example.com")
        self.assertEqual(response.status_code, 302)

    def test_wrong_password_generic_error(self):
        self.make_user("pat@example.com")
        response = self.login("pat@example.com", "wrong")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "correct email address and password")

    def test_pending_applicant_told_application_under_review(self):
        self.apply("app@example.com")
        self.assertContains(self.login("app@example.com"), "still being reviewed")

    def test_pending_applicant_with_wrong_password_gets_generic_error(self):
        self.apply("app@example.com")
        response = self.login("app@example.com", "wrong")
        self.assertNotContains(response, "still being reviewed")

    def test_deactivated_account_told_not_active(self):
        self.make_user("gone@example.com", is_active=False)
        self.assertContains(self.login("gone@example.com"), "isn&#x27;t active")

    def test_admin_login_uses_email(self):
        self.make_user("root@example.com", role="superadmin")
        response = self.client.post("/admin/login/", {"username": "root@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    def test_logout(self):
        client = self.client_for(self.make_user("pat@example.com"))
        client.post("/logout/")
        self.assertRedirectsToLogin(client.get("/users"))


class AccountUrlTests(SiteTestCase):

    def test_password_reset_pages_are_off(self):
        # Off until the site can send email - see config/urls.py.
        for url in ("/password_reset/", "/password_reset/done/", "/reset/x/y/", "/reset/done/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_password_change_works(self):
        user = self.make_user("pat@example.com")
        response = self.client_for(user).post("/password_change/", {
            "old_password": PASSWORD,
            "new_password1": "Brand-new-pass-456",
            "new_password2": "Brand-new-pass-456",
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("Brand-new-pass-456"))

    def test_password_change_requires_login(self):
        self.assertRedirectsToLogin(self.client.get("/password_change/"))


class EnsureSuperuserTests(SiteTestCase):

    def run_command(self, **env):
        out = StringIO()
        with mock.patch.dict(os.environ, env, clear=False):
            call_command("ensure_superuser", stdout=out)
        return out.getvalue()

    def test_missing_variables_is_an_error(self):
        with mock.patch.dict(os.environ, {"DJANGO_SUPERUSER_EMAIL": "", "DJANGO_SUPERUSER_PASSWORD": ""}):
            with self.assertRaises(CommandError):
                call_command("ensure_superuser")

    def test_creates_superuser(self):
        output = self.run_command(DJANGO_SUPERUSER_EMAIL="Admin@Example.com", DJANGO_SUPERUSER_PASSWORD="pw-123456")
        user = User.objects.get(email="admin@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("pw-123456"))
        self.assertIn("Created", output)

    def test_existing_account_left_alone(self):
        self.run_command(DJANGO_SUPERUSER_EMAIL="admin@example.com", DJANGO_SUPERUSER_PASSWORD="first-pass")
        output = self.run_command(DJANGO_SUPERUSER_EMAIL="ADMIN@example.com", DJANGO_SUPERUSER_PASSWORD="second-pass")
        self.assertIn("already exists", output)
        self.assertEqual(User.objects.filter(email="admin@example.com").count(), 1)
        self.assertTrue(User.objects.get(email="admin@example.com").check_password("first-pass"))
