from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateFileSystemStorage(FileSystemStorage):
    """
    Deliberately separate from MEDIA_ROOT/MEDIA_URL: files in this storage
    are only meant to be reachable through an authenticated-or-gated
    Django view, not by anyone who guesses or is handed a public URL.

    FileSystemStorage silently falls back to settings.MEDIA_URL for .url()
    whenever base_url isn't explicitly set - passing base_url=None or ""
    does NOT prevent that fallback, it still resolves to MEDIA_URL. The
    only reliable way to guarantee nothing ever hands out a public link
    for these files is to override url() to refuse outright.

    This is a copy of meetings.storage.PrivateFileSystemStorage rather
    than an import from it: core is the generic, foundational app and
    must not depend on meetings, or any other feature app layered on top
    of it (see the note on INSTALLED_APPS in config/settings.py and the
    comment atop core/urls.py) - meetings depends on core, not the other
    way around, regardless of meetings itself being a required part of
    this template rather than optional. Both classes share the same
    private_media/ directory, so it's one private-files bucket regardless
    of which app's model put a file there.
    """

    def url(self, name):
        raise NotImplementedError(
            "Files in this storage are private - serve them through a "
            "gated view instead of .url()."
        )


# A callable (not a Storage instance) so Django's migrations store a
# reference to private_storage itself rather than inlining the resolved
# BASE_DIR path at makemigrations time - a plain instance would otherwise
# bake *this machine's* absolute path into the migration file.
def private_storage():
    return PrivateFileSystemStorage(location=str(settings.BASE_DIR / "private_media"))
