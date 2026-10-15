"""Shared setup for the site's tests.

Run them with `make test`. Every test case should extend SiteTestCase,
which takes care of what the test environment needs that production
doesn't:

- plain static file storage - the test runner forces DEBUG off, and the
  production storage (WhiteNoise's manifest) would demand a collectstatic
  manifest that doesn't exist in a test run;
- a fast password hasher, so creating users doesn't dominate run time;
- throwaway MEDIA_ROOT / PRIVATE_MEDIA_ROOT folders, so tests that upload
  files never touch the real ones;
- one Organization (the site is single-club - see OrganizationMiddleware),
  plus helpers to create each kind of account and a logged-in client.
"""

import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from core.models import Organization, Resource, ResourceCategory, User

PASSWORD = "Test-password-123"

_MEDIA_ROOT = tempfile.mkdtemp(prefix="test-media-")
_PRIVATE_MEDIA_ROOT = tempfile.mkdtemp(prefix="test-private-media-")


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    MEDIA_ROOT=_MEDIA_ROOT,
    PRIVATE_MEDIA_ROOT=_PRIVATE_MEDIA_ROOT,
)
class SiteTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        # The logo only needs a name for {{ organization.logo.url }} to
        # render - no file has to exist.
        cls.org = Organization.objects.create(
            name="Test Pilots Association",
            logo="logos/test.png",
            airport_icao="KSNS",
            email="info@example.com",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Leave the folders themselves for the next test case; just empty them.
        for root in (_MEDIA_ROOT, _PRIVATE_MEDIA_ROOT):
            shutil.rmtree(root, ignore_errors=True)
            os.makedirs(root, exist_ok=True)

    # ---- accounts ----

    @staticmethod
    def make_user(email, role="member", **extra):
        """role: member / site_admin / officer / superadmin."""
        if role == "superadmin":
            return User.objects.create_superuser(email=email, password=PASSWORD, **extra)
        user = User.objects.create_user(email=email, password=PASSWORD, **extra)
        if role != "member":
            user.set_role(role)
        return user

    @staticmethod
    def client_for(user=None, **defaults):
        client = Client(**defaults)
        if user is not None:
            client.force_login(user)
        return client

    # ---- membership applications ----

    def apply(self, email, first_name="Pat", last_name="Pilot", password=PASSWORD, **extra):
        """Submits the Join page's application as an anonymous visitor."""
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password1": password,
            "password2": password,
            "phone": "",
            "pilot_status": "student",
            "message": "",
            **extra,
        }
        return Client().post("/join", data)

    # ---- files ----

    @staticmethod
    def upload(name="file.pdf", content=b"%PDF-1.4 test"):
        return SimpleUploadedFile(name, content)

    def make_resource(self, title="Bylaws", visibility=Resource.VISIBILITY_PUBLIC, **extra):
        category, _ = ResourceCategory.objects.get_or_create(organization=self.org, title="Forms")
        return Resource.objects.create(
            organization=self.org,
            category=category,
            title=title,
            file=self.upload(f"{title.lower().replace(' ', '-')}.pdf"),
            visibility=visibility,
            **extra,
        )

    # ---- assertions ----

    def assertRedirectsToLogin(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
