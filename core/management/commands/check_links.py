from django.core.management.base import BaseCommand

from core.links import link_error
from core.models import Card, InfoPanel, NavigationItem, Organization

# Which link field(s) to check on each model - kept here rather than
# discovered generically, since not every CharField on these models is a
# link field (e.g. Organization.name, Card.title).
LINK_FIELDS = {
    Organization: [
        "hero_primary_button_url",
        "hero_secondary_button_url",
        "welcome_button_url",
        "join_url",
        "facebook_url",
        "instagram_url",
    ],
    NavigationItem: ["url"],
    Card: ["link"],
    InfoPanel: ["link"],
}


class Command(BaseCommand):
    help = (
        "Checks every stored link field (see core/links.py) against the "
        "site's current URL config and Resource slugs, and reports any "
        "that no longer resolve. A link field only gets re-validated "
        "when its row is next saved through a form or full_clean() (see "
        "each model's clean()), so a row that hasn't been touched since "
        "before a URL was renamed can go stale without anything catching "
        "it - this is the sweep that catches it. Run with --strict (e.g. "
        "in CI, or before a deploy after restructuring core/urls.py) to "
        "exit non-zero on any bad link; without it, this only reports."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with a non-zero status if any link is invalid.",
        )

    def handle(self, *args, **options):
        problems = []

        for model, fields in LINK_FIELDS.items():
            for obj in model.objects.all():
                # InfoPanel.clean() skips validation for a "Next Meeting"
                # panel's link field - it's ignored at render time too
                # (see components/info_panel.html), so flagging it here
                # would be a false positive, not a real dead link.
                if (
                    model is InfoPanel
                    and obj.panel_type == InfoPanel.TYPE_NEXT_MEETING
                ):
                    continue
                for field in fields:
                    value = getattr(obj, field)
                    error = link_error(value)
                    if error:
                        problems.append((model, obj, field, value, error))

        if not problems:
            self.stdout.write(self.style.SUCCESS("All links OK."))
            return

        for model, obj, field, value, error in problems:
            self.stdout.write(
                self.style.WARNING(
                    f"{model.__name__} {obj.pk} ({obj}).{field} = {value!r}: {error}"
                )
            )

        summary = f"{len(problems)} bad link(s) found."
        if options["strict"]:
            self.stderr.write(self.style.ERROR(summary))
            raise SystemExit(1)

        self.stdout.write(self.style.WARNING(summary))
