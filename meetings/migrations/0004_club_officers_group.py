from django.db import migrations


GROUP_NAME = "Club Officers"
PERMISSION_CODENAMES = ["add_meeting", "change_meeting", "delete_meeting"]


def create_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    group, _ = Group.objects.get_or_create(name=GROUP_NAME)

    permissions = Permission.objects.filter(
        content_type__app_label="meetings",
        codename__in=PERMISSION_CODENAMES,
    )
    group.permissions.set(permissions)


def remove_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("meetings", "0003_alter_meeting_location"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_group, remove_group),
    ]
