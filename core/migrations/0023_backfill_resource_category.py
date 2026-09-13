from django.db import migrations

DEFAULT_CATEGORY_TITLE = "Applications & Forms"


def backfill_category(apps, schema_editor):
    Resource = apps.get_model("core", "Resource")
    ResourceCategory = apps.get_model("core", "ResourceCategory")

    uncategorized = Resource.objects.filter(category__isnull=True)
    for resource in uncategorized:
        category, _ = ResourceCategory.objects.get_or_create(
            organization=resource.organization,
            title=DEFAULT_CATEGORY_TITLE,
        )
        resource.category = category
        resource.save(update_fields=["category"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_resource_visibility_alter_resource_file_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_category, noop),
    ]
