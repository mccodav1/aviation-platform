from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Organization

# The fixtures that reproduce the site as it currently looks. Their
# File/ImageField paths only resolve once seed_media has copied the
# matching files out of base_images/ and base_documents/.
FIXTURES = [
    "core/fixtures/spa_demo.json",
]


class Command(BaseCommand):
    help = (
        "One-time content seed for a fresh deployment: copies the seed "
        "media into place (seed_media) and loads the site's fixtures. "
        "Deliberately separate from container startup - it refuses to "
        "run once an Organization exists, since loading the fixtures "
        "again would overwrite anything officers have since edited."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even though content already exists, overwriting the fixture rows.",
        )

    def handle(self, *args, **options):
        if Organization.objects.exists() and not options["force"]:
            raise CommandError(
                "This site already has content - refusing to overwrite it. "
                "Pass --force to reload the fixtures anyway."
            )

        call_command("seed_media", stdout=self.stdout, stderr=self.stderr)
        with transaction.atomic():
            call_command("loaddata", *FIXTURES, stdout=self.stdout, stderr=self.stderr)

        self.stdout.write(self.style.SUCCESS("Site content bootstrapped."))
