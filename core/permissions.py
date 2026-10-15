OFFICER_GROUP_NAME = "Club Officers"
SITE_ADMIN_GROUP_NAME = "Site Admins"

# Officers run the club: meetings, resources, contact messages, and
# membership applications.
OFFICER_PERMISSIONS = [
    ("meetings", "add_event"),
    ("meetings", "change_event"),
    ("meetings", "delete_event"),
    ("core", "add_resource"),
    ("core", "change_resource"),
    ("core", "delete_resource"),
    ("core", "add_resourcecategory"),
    ("core", "change_resourcecategory"),
    ("core", "delete_resourcecategory"),
    ("core", "view_contactmessage"),
    ("core", "change_contactmessage"),
    ("core", "delete_contactmessage"),
    ("core", "view_user"),
    ("core", "view_joinrequest"),
    ("core", "change_joinrequest"),
    ("core", "delete_joinrequest"),
]

# Site admins run the website: its content, and account support
# (unlocking accounts, resetting passwords, assigning these two groups).
# Deliberately not applications or contact messages - those hold
# applicants' personal details, and deciding who joins is officer work.
# No delete_user either: deactivate instead. The admin keeps them away
# from superuser status and superuser accounts (see UserAdmin).
SITE_ADMIN_PERMISSIONS = [
    ("core", "view_user"),
    ("core", "add_user"),
    ("core", "change_user"),
    ("core", "view_organization"),
    ("core", "change_organization"),
    *[
        ("core", f"{action}_{model}")
        for model in ("heroimage", "navigationitem", "card", "highlight", "infopanel", "officer")
        for action in ("view", "add", "change", "delete")
    ],
]

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
