"""Login throttling: 5 failures for one (IP, email) pair lock that pair
out for LOGIN_LOCKOUT_MINUTES."""

from datetime import timedelta

from django.test import Client
from django.utils import timezone

from core import throttle
from core.models import LoginLockout
from core.tests.base import PASSWORD, SiteTestCase


class ThrottleTests(SiteTestCase):

    def setUp(self):
        self.user = self.make_user("pat@example.com")

    def attempt(self, password, ip="1.1.1.1", email="pat@example.com", url="/login/", **headers):
        return Client(REMOTE_ADDR=ip, **headers).post(url, {"username": email, "password": password})

    def fail(self, times, **kwargs):
        for _ in range(times):
            self.attempt("wrong", **kwargs)

    def assertLockedOut(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Too many failed login attempts")

    def test_four_failures_dont_lock(self):
        self.fail(4)
        self.assertEqual(self.attempt(PASSWORD).status_code, 302)

    def test_fifth_failure_locks(self):
        self.fail(4)
        self.assertLockedOut(self.attempt("wrong"))

    def test_correct_password_refused_while_locked(self):
        self.fail(5)
        self.assertLockedOut(self.attempt(PASSWORD))

    def test_other_ip_unaffected(self):
        self.fail(5)
        self.assertEqual(self.attempt(PASSWORD, ip="2.2.2.2").status_code, 302)

    def test_other_email_from_same_ip_unaffected(self):
        self.make_user("other@example.com")
        self.fail(5)
        self.assertEqual(self.attempt(PASSWORD, email="other@example.com").status_code, 302)

    def test_unknown_email_throttled_the_same(self):
        self.fail(4, email="nobody@example.com")
        self.assertLockedOut(self.attempt("wrong", email="nobody@example.com"))

    def test_email_case_doesnt_dodge_the_count(self):
        for email in ("pat@example.com", "PAT@example.com", "Pat@Example.com", "pat@EXAMPLE.com"):
            self.attempt("wrong", email=email)
        self.assertLockedOut(self.attempt("wrong", email="PAT@EXAMPLE.COM"))

    def test_lock_expires(self):
        self.fail(5)
        LoginLockout.objects.update(locked_until=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.attempt(PASSWORD).status_code, 302)

    def test_old_failures_dont_count_toward_a_new_burst(self):
        self.fail(4)
        LoginLockout.objects.update(last_failure_at=timezone.now() - timedelta(hours=1))
        self.attempt("wrong")
        self.assertEqual(LoginLockout.objects.get().failed_attempts, 1)

    def test_success_clears_failures(self):
        self.fail(4)
        self.attempt(PASSWORD)
        self.assertFalse(LoginLockout.objects.exists())

    def test_admin_login_throttled_and_counts(self):
        self.fail(5, url="/admin/login/")
        self.assertLockedOut(self.attempt(PASSWORD))

    def test_site_lockout_blocks_admin_login_too(self):
        self.fail(5)
        response = self.attempt(PASSWORD, url="/admin/login/")
        self.assertContains(response, "Too many failed login attempts")

    def test_inactive_account_correct_password_not_counted(self):
        self.make_user("gone@example.com", is_active=False)
        for _ in range(6):
            self.attempt(PASSWORD, email="gone@example.com")
        self.assertFalse(LoginLockout.objects.filter(locked_until__isnull=False).exists())

    def test_last_forwarded_for_entry_is_the_client(self):
        # nginx appends the real address; anything before it is client-supplied.
        self.fail(5, ip="10.0.0.1", HTTP_X_FORWARDED_FOR="9.9.9.9, 1.1.1.1")
        self.assertLockedOut(self.attempt(PASSWORD, ip="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1"))
        self.assertEqual(
            self.attempt(PASSWORD, ip="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1, 9.9.9.9").status_code, 302,
        )

    def test_unlock_clears_every_ip(self):
        self.fail(5, ip="1.1.1.1")
        self.fail(5, ip="2.2.2.2")
        throttle.unlock("PAT@example.com")
        self.assertEqual(throttle.locked_emails(), set())
        self.assertEqual(self.attempt(PASSWORD, ip="2.2.2.2").status_code, 302)

    def test_locked_emails(self):
        self.fail(5)
        self.assertEqual(throttle.locked_emails(), {"pat@example.com"})
