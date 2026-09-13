from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from .storage import private_storage

# Kept to common document formats - also keeps FileResponse's content-type
# guessing in meeting_agenda_download/meeting_minutes_download landing on
# safe, non-executable types for inline display.
ALLOWED_MEETING_FILE_EXTENSIONS = ["pdf", "doc", "docx", "odt", "rtf", "txt"]


# Create your models here.
class Meeting(models.Model):
    organization = models.ForeignKey(
        "core.Organization",
        on_delete=models.CASCADE,
        related_name="meetings",
    )

    title = models.CharField(
        max_length=255,
        default="Monthly Meeting"
    )

    starts_at = models.DateTimeField()

    location = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    is_cancelled = models.BooleanField(default=False)

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
        return f"{self.title} - {self.starts_at:%Y-%m-%d}"

