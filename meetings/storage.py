from django.conf import settings

# meetings depends on core (never the other way - see the "make
# optional" note on INSTALLED_APPS in config/settings.py and the
# comment atop core/urls.py), so the actual private-storage class lives
# once in core/storage.py and this module just reuses it, rather than
# keeping a second, drifting copy of the same class.
from core.storage import PrivateFileSystemStorage

__all__ = ["PrivateFileSystemStorage", "private_storage"]


# A callable (not a Storage instance) so Django's migrations store a
# reference to private_storage itself rather than inlining the resolved
# BASE_DIR path at makemigrations time - a plain instance would otherwise
# bake *this machine's* absolute path into the migration file. Kept as
# its own function (rather than importing core.storage.private_storage
# directly) so historical migrations that reference
# "meetings.storage.private_storage" by dotted path keep resolving.
def private_storage():
    return PrivateFileSystemStorage(location=str(settings.BASE_DIR / "private_media"))
