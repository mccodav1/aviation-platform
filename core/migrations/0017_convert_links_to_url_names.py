from django.db import migrations
from django.urls import Resolver404, resolve

# One-off conversion of link fields from hand-typed paths (e.g.
# "/events") to the Django URL name they should have been all along
# (e.g. "core:events") - see core/links.py for why. This necessarily
# resolves against the *current* core/urls.py, not a frozen historical
# one, since the whole point is to match what's live today.

_ABSOLUTE_PREFIXES = ("http://", "https://", "//", "mailto:", "tel:")

FIELDS_BY_MODEL = {
    "NavigationItem": ["url"],
    "Card": ["link"],
    "InfoPanel": ["link"],
    "Organization": [
        "hero_primary_button_url",
        "hero_secondary_button_url",
        "welcome_button_url",
        "join_url",
    ],
}


def _is_absolute(value):
    return bool(value) and value.startswith(_ABSOLUTE_PREFIXES)


def _path_to_url_name(path):
    """Best-effort: resolve a legacy path-style value to the URL name
    it matches, retrying with a leading slash in case the stored value
    was missing one. Returns None if nothing matches."""
    candidates = [path] if path.startswith("/") else [path, "/" + path]
    for candidate in candidates:
        try:
            return resolve(candidate).view_name
        except Resolver404:
            continue
    return None


def convert_links_forward(apps, schema_editor):
    unresolved = []

    for model_name, field_names in FIELDS_BY_MODEL.items():
        Model = apps.get_model("core", model_name)
        for instance in Model.objects.all():
            changed_fields = []
            for field_name in field_names:
                value = getattr(instance, field_name)
                if not value or _is_absolute(value):
                    continue
                url_name = _path_to_url_name(value)
                if url_name is None:
                    unresolved.append(
                        f"{model_name} {instance.pk} {field_name}={value!r}"
                    )
                    continue
                setattr(instance, field_name, url_name)
                changed_fields.append(field_name)
            if changed_fields:
                instance.save(update_fields=changed_fields)

    if unresolved:
        print(
            "\n"
            "WARNING: 0017_convert_links_to_url_names could not resolve "
            "these existing link values to a URL name. They were left "
            "as-is and need a manual look in the admin:\n  "
            + "\n  ".join(unresolved)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_infopanel_panel_type"),
    ]

    operations = [
        migrations.RunPython(convert_links_forward, migrations.RunPython.noop),
    ]
