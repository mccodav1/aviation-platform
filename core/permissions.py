OFFICER_GROUP_NAME = "Club Officers"
SITE_ADMIN_GROUP_NAME = "Site Admins"


def _crud(app_label, *models):
    return [
        (app_label, f"{action}_{model}")
        for model in models
        for action in ("view", "add", "change", "delete")
    ]


# What both roles can do: run meetings/events and resources, keep the
# site's content up to date, and handle account support (unlocking
# accounts, resetting passwords, editing names/emails, creating
# accounts). No delete_user for either - deactivate instead; deleting is
# superuser-only.
# The admin keeps both away from superuser status and superuser
# accounts (see UserAdmin).
SHARED_PERMISSIONS = [
    *_crud("meetings", "event"),
    *_crud("core", "resource", "resourcecategory"),
    ("core", "view_organization"),
    ("core", "change_organization"),
    *_crud("core", "heroimage", "navigationitem", "card", "highlight", "infopanel", "officer"),
    ("core", "view_user"),
    ("core", "add_user"),
    ("core", "change_user"),
    # Sending messages to members' Inboxes (add), seeing what's been sent
    # (view), and deleting from the Sent log (delete).
    ("core", "add_membermessage"),
    ("core", "view_membermessage"),
    ("core", "delete_membermessage"),
]

# Officers additionally handle membership applications (reviewing,
# approving/denying, deleting) and contact messages - both hold people's
# personal details and are meant for the club's officers only - and
# decide who holds a role.
OFFICER_PERMISSIONS = SHARED_PERMISSIONS + [
    ("core", "assign_roles"),
    ("core", "view_joinrequest"),
    ("core", "change_joinrequest"),
    ("core", "delete_joinrequest"),
    ("core", "view_contactmessage"),
    ("core", "change_contactmessage"),
    ("core", "delete_contactmessage"),
]

# Site admins run the website alongside the officers - everything shared,
# but no applications, contact messages, or changing roles. So the roles
# are a ladder: Officer can do everything Site admin can, and more (see
# User.ROLE_CHOICES) - keep OFFICER_PERMISSIONS a superset of this.
SITE_ADMIN_PERMISSIONS = SHARED_PERMISSIONS

# Each group's permissions, as (app_label, codename). Synced after every
# `migrate` (see CoreConfig.ready) rather than by a data migration: Django
# only creates model permissions at the end of a migrate run, so on a
# fresh database a migration looking them up finds nothing. Add-only -
# removing an entry here doesn't revoke it from an existing group; do
# that in /admin.
GROUP_PERMISSIONS = {
    OFFICER_GROUP_NAME: OFFICER_PERMISSIONS,
    SITE_ADMIN_GROUP_NAME: SITE_ADMIN_PERMISSIONS,
}


def sync_role_groups(apps, **kwargs):
    """post_migrate receiver. post_migrate fires once per installed app,
    and each app's permissions only exist once its own signal has run, so
    this runs on every one of them - the last call sees them all."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for group_name, permissions in GROUP_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        for app_label, codename in permissions:
            permission = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename,
            ).first()
            if permission:
                group.permissions.add(permission)
