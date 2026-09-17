from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from .storage import private_storage

# Kept to common document formats - also keeps FileResponse's content-type
# guessing in meeting_agenda_download/meeting_minutes_download landing on
# safe, non-executable types for inline display.
ALLOWED_MEETING_FILE_EXTENSIONS = ["pdf", "doc", "docx", "odt", "rtf", "txt"]


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

    def __str__(self):
        # starts_at is stored as an aware UTC instant - format it in the
        # org's local timezone (see TIME_ZONE in settings) rather than
        # raw-formatting the UTC value directly, which could show the
        # wrong calendar date for an event near local midnight.
        return f"{self.title} - {timezone.localtime(self.starts_at):%Y-%m-%d}"
