from django.conf import settings

# The private-storage class lives once in core/storage.py; this module
# just reuses it rather than keeping a second copy.
from core.storage import PrivateFileSystemStorage

__all__ = ["PrivateFileSystemStorage", "private_storage"]


# A callable (not a Storage instance) so Django's migrations store a
# reference to private_storage itself rather than inlining the resolved
# PRIVATE_MEDIA_ROOT path at makemigrations time - a plain instance would otherwise
# bake *this machine's* absolute path into the migration file. Kept as
# its own function (rather than importing core.storage.private_storage
# directly) so historical migrations that reference
# "meetings.storage.private_storage" by dotted path keep resolving.
def private_storage():
    return PrivateFileSystemStorage(location=str(settings.PRIVATE_MEDIA_ROOT))
