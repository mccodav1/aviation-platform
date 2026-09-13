import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Maps a file under a tracked source directory to where it should be
# copied under MEDIA_ROOT. base_images/ and base_documents/ are the
# template's tracked seed assets; media/ is per-deployment, generated/
# uploaded output and isn't tracked in git, so it needs to be
# reconstructed on a fresh clone before the fixtures' File/ImageField
# paths (see core/fixtures, meetings/fixtures) resolve to real files.
SOURCE_DIRS_TO_ASSETS = {
    "base_images": {
        "hero/coastline.jpg": "hero/coastline.jpg",
        "hero/distant.jpg": "hero/distant.jpg",
        "hero/lonepine.png": "hero/lonepine.png",
        "logos/salinaslogolong.png": "logos/salinaslogolong.png",
    },
    "base_documents": {
        "scholarship-application.pdf": "resources/scholarship-application.pdf",
    },
}


class Command(BaseCommand):
    help = "Copies seed files from base_images/ and base_documents/ into media/ so fixture-loaded records resolve to real files."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)

        for source_dir, assets in SOURCE_DIRS_TO_ASSETS.items():
            source_root = Path(settings.BASE_DIR) / source_dir

            for source_rel, dest_rel in assets.items():
                source_path = source_root / source_rel
                dest_path = media_root / dest_rel

                if not source_path.exists():
                    self.stderr.write(f"Missing source file: {source_path}")
                    continue

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_path, dest_path)
                self.stdout.write(f"Copied {source_dir}/{source_rel} -> media/{dest_rel}")

        self.stdout.write(self.style.SUCCESS("Done."))
