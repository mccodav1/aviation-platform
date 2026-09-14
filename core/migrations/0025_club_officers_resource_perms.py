from django.db import migrations

# Same "Club Officers" group meetings/migrations/0004_club_officers_group.py
# creates - get_or_create here too since core must not depend on the
# optional meetings app (this migration has to work whether or not
# meetings is installed). Uses .add() rather than .set() so that
# whichever of the two migrations runs first, it only ever adds its own
# app's permissions to the group instead of overwriting the other's.
GROUP_NAME = "Club Officers"
PERMISSION_CODENAMES = [
    "add_resource", "change_resource", "delete_resource",
    "add_resourcecategory", "change_resourcecategory", "delete_resourcecategory",
]


def add_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    group, _ = Group.objects.get_or_create(name=GROUP_NAME)

    permissions = Permission.objects.filter(
        content_type__app_label="core",
        codename__in=PERMISSION_CODENAMES,
    )
    group.permissions.add(*permissions)


def remove_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    try:
        group = Group.objects.get(name=GROUP_NAME)
    except Group.DoesNotExist:
        return

    permissions = Permission.objects.filter(
        content_type__app_label="core",
        codename__in=PERMISSION_CODENAMES,
    )
    group.permissions.remove(*permissions)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_alter_resource_category"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
