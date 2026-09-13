from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateFileSystemStorage(FileSystemStorage):
    """
    Deliberately separate from MEDIA_ROOT/MEDIA_URL: agenda/minutes files
    are only meant to be reachable by authenticated users through
    meeting_agenda_download/meeting_minutes_download (meetings/views.py),
    not by anyone who guesses or is handed a public URL.

    FileSystemStorage silently falls back to settings.MEDIA_URL for .url()
    whenever base_url isn't explicitly set - passing base_url=None or ""
    does NOT prevent that fallback, it still resolves to MEDIA_URL. The
    only reliable way to guarantee nothing ever hands out a public link
    for these files is to override url() to refuse outright.
    """

    def url(self, name):
        raise NotImplementedError(
            "Files in this storage are private - serve them through an "
            "authenticated view (see meetings/views.py) instead of .url()."
        )


# A callable (not a Storage instance) so Django's migrations store a
# reference to private_storage itself rather than inlining the resolved
# BASE_DIR path at makemigrations time - a plain instance would otherwise
# bake *this machine's* absolute path into the migration file.
def private_storage():
    return PrivateFileSystemStorage(location=str(settings.BASE_DIR / "private_media"))
