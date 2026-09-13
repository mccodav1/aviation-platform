from django.forms import ClearableFileInput


class PrivateClearableFileInput(ClearableFileInput):
    """
    Like ClearableFileInput, but never touches .url - which raises on
    purpose for fields using PrivateFileSystemStorage (see
    meetings/storage.py). The built-in is_initial() does
    getattr(value, "url", False), and getattr's default only swallows
    AttributeError, not our NotImplementedError, so that has to be
    overridden too, not just the template that renders "Currently: <a
    href=...>" (replaced here with plain text).
    """

    template_name = "widgets/private_clearable_file_input.html"

    def is_initial(self, value):
        return bool(value)
