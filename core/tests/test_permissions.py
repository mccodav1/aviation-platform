"""The role ladder: Member < Site admin < Officer < Superadmin."""

from django.contrib.auth.models import Group
from django.core.management import call_command

from core.permissions import (
    GROUP_PERMISSIONS, OFFICER_GROUP_NAME, OFFICER_PERMISSIONS, SITE_ADMIN_GROUP_NAME,
    SITE_ADMIN_PERMISSIONS,
)
from core.tests.base import SiteTestCase


def codenames(group_name):
    return set(Group.objects.get(name=group_name).permissions.values_list("codename", flat=True))


class GroupSyncTests(SiteTestCase):

    def test_groups_exist_with_every_listed_permission(self):
        # Synced by the post_migrate hook - including on a fresh test DB,
        # which is exactly the case the old data migrations got wrong.
        for group_name, permissions in GROUP_PERMISSIONS.items():
            with self.subTest(group=group_name):
                self.assertEqual(codenames(group_name), {codename for _, codename in permissions})

    def test_officer_permissions_are_a_superset_of_site_admin(self):
        self.assertTrue(set(SITE_ADMIN_PERMISSIONS) <= set(OFFICER_PERMISSIONS))

    def test_officer_only_permissions(self):
        officer_only = codenames(OFFICER_GROUP_NAME) - codenames(SITE_ADMIN_GROUP_NAME)
        self.assertEqual(officer_only, {
            "assign_roles",
            "view_joinrequest", "change_joinrequest", "delete_joinrequest",
            "view_contactmessage", "change_contactmessage", "delete_contactmessage",
        })

    def test_nobody_but_superusers_can_delete_users(self):
        for group_name in (OFFICER_GROUP_NAME, SITE_ADMIN_GROUP_NAME):
            self.assertNotIn("delete_user", codenames(group_name))

    def test_sync_is_idempotent_and_repairs(self):
        group = Group.objects.get(name=OFFICER_GROUP_NAME)
        group.permissions.clear()
        call_command("migrate", verbosity=0)  # fires post_migrate again
        call_command("migrate", verbosity=0)
        self.assertEqual(codenames(OFFICER_GROUP_NAME), {c for _, c in OFFICER_PERMISSIONS})


class SetRoleTests(SiteTestCase):

    def test_each_role_means_exactly_one_group_and_staff_follows(self):
        user = self.make_user("u@example.com")
        extra = Group.objects.create(name="Newsletter")
        user.groups.add(extra)
        for role, group, staff in (
            ("site_admin", SITE_ADMIN_GROUP_NAME, True),
            ("officer", OFFICER_GROUP_NAME, True),
            ("member", None, False),
        ):
            with self.subTest(role=role):
                user.set_role(role)
                user.refresh_from_db()
                role_groups = set(user.groups.exclude(name="Newsletter").values_list("name", flat=True))
                self.assertEqual(role_groups, {group} if group else set())
                self.assertEqual(user.is_staff, staff)
                self.assertTrue(user.groups.filter(name="Newsletter").exists())

    def test_role_labels(self):
        self.assertEqual(self.make_user("a@example.com").role, "Member")
        self.assertEqual(self.make_user("b@example.com", role="site_admin").role, "Site admin")
        self.assertEqual(self.make_user("c@example.com", role="officer").role, "Officer")
        self.assertEqual(self.make_user("d@example.com", role="superadmin").role, "Superadmin")
        self.assertEqual(self.make_user("e@example.com", is_staff=True).role, "Staff")

    def test_account_in_both_groups_reads_as_officer(self):
        user = self.make_user("both@example.com")
        user.groups.add(*Group.objects.filter(name__in=[OFFICER_GROUP_NAME, SITE_ADMIN_GROUP_NAME]))
        self.assertEqual(user.role_choice, "officer")


class OfficerPageAccessTests(SiteTestCase):
    """Who can open each officer-only page: visitors are sent to log in,
    members are refused, and each role gets exactly its pages."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.member = cls.make_user("member@example.com")
        cls.site_admin = cls.make_user("sa@example.com", role="site_admin")
        cls.officer = cls.make_user("officer@example.com", role="officer")

    # url -> (site admin allowed, officer allowed)
    PAGES = {
        "/users": (True, True),
        "/applications": (False, True),
        "/messages": (False, True),
        "/meetings/add": (True, True),
        "/resources/add": (True, True),
        "/admin/core/user/": (True, True),
        "/admin/core/card/": (True, True),
        "/admin/meetings/event/": (True, True),
        "/admin/core/joinrequest/": (False, True),
        "/admin/core/contactmessage/": (False, True),
        "/admin/auth/group/": (False, False),
    }

    def test_access_matrix(self):
        clients = {
            "site_admin": self.client_for(self.site_admin),
            "officer": self.client_for(self.officer),
        }
        for url, (site_admin_ok, officer_ok) in self.PAGES.items():
            for who, allowed in (("site_admin", site_admin_ok), ("officer", officer_ok)):
                with self.subTest(url=url, who=who):
                    status = clients[who].get(url).status_code
                    self.assertEqual(status, 200 if allowed else 403)

    def test_member_refused_and_visitor_sent_to_login(self):
        member = self.client_for(self.member)
        for url in ("/users", "/applications", "/messages", "/meetings/add", "/resources/add"):
            with self.subTest(url=url):
                self.assertEqual(member.get(url).status_code, 403)
                self.assertRedirectsToLogin(self.client.get(url))
