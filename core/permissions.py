OFFICER_GROUP_NAME = "Club Officers"

# Everything the Club Officers group is granted, as (app_label, codename).
# Synced after every `migrate` (see CoreConfig.ready) rather than by a
# data migration: Django only creates model permissions at the end of a
# migrate run, so on a fresh database a migration looking them up finds
# nothing. Add-only - removing an entry here doesn't revoke it from an
# existing group; do that in /admin.
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
    ("core", "view_joinrequest"),
    ("core", "change_joinrequest"),
    ("core", "delete_joinrequest"),
]


def sync_officer_group(apps, **kwargs):
    """post_migrate receiver. post_migrate fires once per installed app,
    and each app's permissions only exist once its own signal has run, so
    this runs on every one of them - the last call sees them all."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    group, _ = Group.objects.get_or_create(name=OFFICER_GROUP_NAME)
    for app_label, codename in OFFICER_PERMISSIONS:
        permission = Permission.objects.filter(
            content_type__app_label=app_label, codename=codename,
        ).first()
        if permission:
            group.permissions.add(permission)
