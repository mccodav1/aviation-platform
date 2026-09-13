import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Maps a file under base_images/ to where it should be copied under
# MEDIA_ROOT. base_images/ is the template's tracked source imagery;
# media/ is per-deployment, generated/uploaded output and isn't tracked
# in git, so it needs to be reconstructed on a fresh clone before the
# fixtures' ImageField paths (see core/fixtures, meetings/fixtures)
# resolve to real files.
ASSETS = {
    "hero/coastline.jpg": "hero/coastline.jpg",
    "hero/distant.jpg": "hero/distant.jpg",
    "hero/lonepine.png": "hero/lonepine.png",
    "logos/salinaslogolong.png": "logos/salinaslogolong.png",
}


class Command(BaseCommand):
    help = "Copies seed images from base_images/ into media/ so fixture-loaded records resolve to real files."

    def handle(self, *args, **options):
        source_root = Path(settings.BASE_DIR) / "base_images"
        media_root = Path(settings.MEDIA_ROOT)

        for source_rel, dest_rel in ASSETS.items():
            source_path = source_root / source_rel
            dest_path = media_root / dest_rel

            if not source_path.exists():
                self.stderr.write(f"Missing source image: {source_path}")
                continue

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, dest_path)
            self.stdout.write(f"Copied {source_rel} -> media/{dest_rel}")

        self.stdout.write(self.style.SUCCESS("Done."))
