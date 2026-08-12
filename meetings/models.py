from django.db import models
from django.utils import timezone


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

    @property
    def is_past(self):
        return self.starts_at < timezone.now()

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.title} - {self.starts_at:%Y-%m-%d}"

