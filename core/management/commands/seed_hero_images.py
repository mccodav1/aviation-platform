from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from core.models import HeroImage


class Command(BaseCommand):
    help = "Imports hero images from media_seed/hero"

    def handle(self, *args, **options):
        image_dir = Path(settings.BASE_DIR) / "media" / "hero"

        if not image_dir.exists():
            self.stderr.write(f"{image_dir} does not exist.")
            return

        order = HeroImage.objects.count()

        for path in sorted(image_dir.iterdir()):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue

            if HeroImage.objects.filter(title=path.stem).exists():
                self.stdout.write(f"Skipping {path.name}")
                continue

            with path.open("rb") as f:
                HeroImage.objects.create(
                    title=path.stem,
                    order=order,
                    image=File(f, name=path.name),
                )

            order += 1
            self.stdout.write(f"Imported {path.name}")

        self.stdout.write(self.style.SUCCESS("Done."))