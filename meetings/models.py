from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from .storage import private_storage

# Kept to common document formats - also keeps FileResponse's content-type
# guessing in meeting_agenda_download/meeting_minutes_download landing on
# safe, non-executable types for inline display.
ALLOWED_MEETING_FILE_EXTENSIONS = ["pdf", "doc", "docx", "odt", "rtf", "txt"]

# Other attachments can be anything a meeting tends to produce - a
# treasurer's spreadsheet, a slide deck, photos - but still nothing a
# browser would run (no html/svg/js), for the same reason as above.
ALLOWED_ATTACHMENT_FILE_EXTENSIONS = ALLOWED_MEETING_FILE_EXTENSIONS + [
    "xls", "xlsx", "ods", "csv", "ppt", "pptx", "odp", "png", "jpg", "jpeg",
]


class Event(models.Model):
    TYPE_MEETING = "meeting"
    TYPE_FLYOUT = "flyout"
    TYPE_AIRSHOW = "airshow"
    TYPE_SOCIAL = "social"
    TYPE_OTHER = "other"

    TYPE_CHOICES = [
        (TYPE_MEETING, "Meeting"),
        (TYPE_FLYOUT, "Fly-Out"),
        (TYPE_AIRSHOW, "Airshow"),
        (TYPE_SOCIAL, "Social"),
        (TYPE_OTHER, "Other"),
    ]

    organization = models.ForeignKey(
        "core.Organization",
        on_delete=models.CASCADE,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_MEETING,
    )

    title = models.CharField(max_length=255)

    starts_at = models.DateTimeField()

    location = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    is_cancelled = models.BooleanField(default=False)

    # Meeting-only in practice (only rendered/managed for TYPE_MEETING -
    # see app/meeting_detail.html) rather than split into a separate
    # model - every other field on this model is common to any event
    # type, and these two don't carry enough of their own behavior to
    # justify a whole side-table.
    agenda = models.FileField(
        upload_to="agendas/",
        storage=private_storage,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_MEETING_FILE_EXTENSIONS)],
    )
    minutes = models.FileField(
        upload_to="minutes/",
        storage=private_storage,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_MEETING_FILE_EXTENSIONS)],
    )

    @property
    def is_past(self):
        return self.starts_at < timezone.now()

    class Meta:
        ordering = ["starts_at"]

    def delete_with_files(self):
        # Deleting the row doesn't delete its uploaded files - remove them
        # from private storage too, so nothing is left orphaned there.
        files = [f for f in (self.agenda, self.minutes) if f]
        files += [attachment.file for attachment in self.attachments.all()]
        self.delete()
        for file in files:
            file.storage.delete(file.name)

    def __str__(self):
        # starts_at is stored as an aware UTC instant - format it in the
        # active timezone (the visitor's browser zone, see
        # core/middleware/timezone.py) rather than raw-formatting the UTC
        # value directly, which could show the wrong calendar date for an
        # event near local midnight.
        return f"{self.title} - {timezone.localtime(self.starts_at):%Y-%m-%d}"


class EventAttachment(models.Model):
    """Any other file attached to a meeting, beyond its agenda and
    minutes (which stay their own fields - every meeting has a slot for
    each). Like those, private, and downloadable by any signed-in user."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attachments")
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to="event_attachments/",
        storage=private_storage,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_ATTACHMENT_FILE_EXTENSIONS)],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return self.title

