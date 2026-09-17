import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Maps a tracked source directory to (destination root, {source: dest})
# pairs. base_images/ and base_documents/ are the template's tracked
# seed assets; media/ and private_media/ are per-deployment, generated/
# uploaded output and aren't tracked in git, so they need to be
# reconstructed on a fresh clone before the fixtures' File/ImageField
# paths (see core/fixtures, meetings/fixtures) resolve to real files.
#
# base_documents/ seeds into private_media/ rather than media/ - every
# Resource file lives in private storage regardless of its visibility
# (see core/storage.py and Resource in core/models.py), so there's
# nowhere under public MEDIA_ROOT for a seeded document to go.
SOURCE_DIRS = {
    "base_images": {
        "dest_root": lambda: Path(settings.MEDIA_ROOT),
        "assets": {
            "hero/coastline-sunset-2.png": "hero/coastline-sunset-2.png",
            "hero/coastline-sunset.png": "hero/coastline-sunset.png",
            "hero/coastline.jpg": "hero/coastline.jpg",
            "hero/distant.jpg": "hero/distant.jpg",
            "hero/lonepine.png": "hero/lonepine.png",
            "logos/salinaslogolong.png": "logos/salinaslogolong.png",
            "cards/fly-with-us.png": "cards/fly-with-us.png",
            "cards/monthly-meetings.jpeg": "cards/monthly-meetings.jpeg",
            "cards/scholarship.png": "cards/scholarship.png",
            "cards/young-eagles.png": "cards/young-eagles.png",
            "welcome/valleyskyline.jpeg": "welcome/valleyskyline.jpeg",
            "about/monterey-coast.jpg": "about/monterey-coast.jpg",
            "about/autogen.png": "about/autogen.png",
        },
    },
    "base_documents": {
        "dest_root": lambda: Path(settings.BASE_DIR) / "private_media",
        "assets": {
            "scholarship-application.pdf": "resources/scholarship-application.pdf",
            "Cessna_172M.pdf": "resources/Cessna_172M.pdf",
        },
    },
}


class Command(BaseCommand):
    help = "Copies seed files from base_images/ and base_documents/ into media/ or private_media/ so fixture-loaded records resolve to real files."

    def handle(self, *args, **options):
        for source_dir, config in SOURCE_DIRS.items():
            source_root = Path(settings.BASE_DIR) / source_dir
            dest_root = config["dest_root"]()

            for source_rel, dest_rel in config["assets"].items():
                source_path = source_root / source_rel
                dest_path = dest_root / dest_rel

                if not source_path.exists():
                    self.stderr.write(f"Missing source file: {source_path}")
                    continue

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_path, dest_path)
                self.stdout.write(f"Copied {source_dir}/{source_rel} -> {dest_path}")

        self.stdout.write(self.style.SUCCESS("Done."))
