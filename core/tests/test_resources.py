"""Resources: who sees and downloads what, and officers adding, editing,
hiding and deleting them."""

import os

from core.models import Resource, ResourceCategory
from core.tests.base import SiteTestCase


def stored(file_field_or_name, storage=None):
    name = getattr(file_field_or_name, "name", file_field_or_name)
    storage = storage or file_field_or_name.storage
    return storage.exists(name)


class ResourceVisibilityTests(SiteTestCase):

    def setUp(self):
        self.public = self.make_resource("Bylaws")
        self.members_only = self.make_resource("Roster", visibility=Resource.VISIBILITY_MEMBERS)
        self.disabled = self.make_resource("Old Form", is_enabled=False)
        self.member_client = self.client_for(self.make_user("member@example.com"))

    def download(self, client, resource):
        return client.get(f"/resources/{resource.slug}/download")

    def test_visitor_sees_public_only(self):
        html = self.client.get("/resources").content.decode()
        self.assertIn("Bylaws", html)
        self.assertNotIn("Roster", html)
        self.assertNotIn("Old Form", html)

    def test_member_sees_members_only_too(self):
        html = self.member_client.get("/resources").content.decode()
        self.assertIn("Roster", html)
        self.assertNotIn("Old Form", html)

    def test_officer_sees_disabled(self):
        officer = self.client_for(self.make_user("officer@example.com", role="officer"))
        self.assertContains(officer.get("/resources"), "Old Form")

    def test_downloads(self):
        self.assertEqual(self.download(self.client, self.public).status_code, 200)
        self.assertRedirectsToLogin(self.download(self.client, self.members_only))
        self.assertEqual(self.download(self.member_client, self.members_only).status_code, 200)
        self.assertEqual(self.download(self.member_client, self.disabled).status_code, 404)

    def test_download_serves_the_file(self):
        response = self.download(self.client, self.public)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 test")

    def test_private_files_have_no_public_url(self):
        with self.assertRaises(NotImplementedError):
            self.public.file.url

    def test_slug_generated_and_unique(self):
        second = self.make_resource("Bylaws")
        self.assertEqual(self.public.slug, "bylaws")
        self.assertEqual(second.slug, "bylaws-2")


class ResourceManagementTests(SiteTestCase):

    def setUp(self):
        self.site_admin_client = self.client_for(self.make_user("sa@example.com", role="site_admin"))
        self.member_client = self.client_for(self.make_user("member@example.com"))
        self.resource = self.make_resource("Bylaws")
        self.category = self.resource.category

    def form_data(self, **overrides):
        return {
            "title": "Bylaws", "description": "", "category": self.category.pk, "visibility": "public",
            **overrides,
        }

    def test_create(self):
        response = self.site_admin_client.post("/resources/add", self.form_data(
            title="Safety Brief", file=self.upload("brief.pdf"),
        ))
        self.assertEqual(response.status_code, 302)
        created = Resource.objects.get(title="Safety Brief")
        self.assertEqual(created.organization, self.org)
        self.assertTrue(stored(created.file))

    def test_create_rejects_disallowed_file_type(self):
        response = self.site_admin_client.post("/resources/add", self.form_data(
            title="Bad", file=self.upload("evil.html", b"<script>"),
        ))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Resource.objects.filter(title="Bad").exists())

    def test_edit_keeps_file_when_none_uploaded(self):
        original = self.resource.file.name
        self.site_admin_client.post(f"/resources/{self.resource.slug}/edit", self.form_data(
            title="Club Bylaws", visibility="members",
        ))
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.title, "Club Bylaws")
        self.assertEqual(self.resource.visibility, "members")
        self.assertEqual(self.resource.file.name, original)
        self.assertEqual(self.resource.slug, "bylaws")  # links keep working after a rename

    def test_edit_page_shows_current_file(self):
        response = self.site_admin_client.get(f"/resources/{self.resource.slug}/edit")
        self.assertContains(response, "Edit Resource")
        self.assertContains(response, os.path.basename(self.resource.file.name))

    def test_replacing_file_removes_the_old_one(self):
        old = self.resource.file.name
        storage = self.resource.file.storage
        self.site_admin_client.post(f"/resources/{self.resource.slug}/edit", self.form_data(
            file=self.upload("new.pdf"),
        ))
        self.resource.refresh_from_db()
        self.assertFalse(storage.exists(old))
        self.assertTrue(storage.exists(self.resource.file.name))

    def test_delete_removes_row_and_file(self):
        name, storage = self.resource.file.name, self.resource.file.storage
        self.site_admin_client.post(f"/resources/{self.resource.slug}/delete")
        self.assertFalse(Resource.objects.exists())
        self.assertFalse(storage.exists(name))

    def test_toggle_enabled(self):
        self.site_admin_client.post(f"/resources/{self.resource.slug}/toggle")
        self.resource.refresh_from_db()
        self.assertFalse(self.resource.is_enabled)

    def test_category_create_returns_escaped_option(self):
        response = self.site_admin_client.post("/resources/categories/add", {"title": "<b>Minutes</b>"})
        self.assertEqual(response.status_code, 201)
        self.assertIn("&lt;b&gt;Minutes&lt;/b&gt;", response.content.decode())
        self.assertTrue(ResourceCategory.objects.filter(title="<b>Minutes</b>").exists())

    def test_category_create_blank_rejected(self):
        self.assertEqual(self.site_admin_client.post("/resources/categories/add", {"title": "  "}).status_code, 400)

    def test_member_refused(self):
        slug = self.resource.slug
        self.assertEqual(self.member_client.get(f"/resources/{slug}/edit").status_code, 403)
        for action in ("delete", "toggle"):
            with self.subTest(action=action):
                self.assertEqual(self.member_client.post(f"/resources/{slug}/{action}").status_code, 403)
        self.assertTrue(Resource.objects.filter(pk=self.resource.pk, is_enabled=True).exists())

    def test_delete_requires_post(self):
        self.assertEqual(self.site_admin_client.get(f"/resources/{self.resource.slug}/delete").status_code, 405)


class ScholarshipPageTests(SiteTestCase):

    def test_download_button_found_by_slug_and_survives_rename(self):
        application = self.make_resource("Scholarship Application")
        self.assertEqual(application.slug, "scholarship-application")
        link = "/resources/scholarship-application/download"
        self.assertContains(self.client.get("/scholarship"), link)
        application.title = "2027 Scholarship Application Form"
        application.save()
        self.assertContains(self.client.get("/scholarship"), link)

    def test_no_button_when_disabled(self):
        self.make_resource("Scholarship Application", is_enabled=False)
        self.assertNotContains(self.client.get("/scholarship"), "/resources/scholarship-application/download")
