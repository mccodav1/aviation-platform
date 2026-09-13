import uuid

from django.core.exceptions import ValidationError
from django.db import models

from core.links import link_error

LINK_HELP_TEXT = (
    'Internal page: its URL name, e.g. "core:events". '
    'Off-site link: full address starting with "https://", "mailto:", '
    'or "tel:".'
)


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="logos/")
    airport_icao = models.CharField(
        max_length=4,
        blank=True,
        help_text="ICAO airport identifier, e.g. KSNS"
    )

    # Hero
    hero_title = models.CharField(max_length=200, default="Hero Title")
    hero_subtitle = models.CharField(max_length=200, default="Hero Subtitle")
    hero_description = models.TextField(blank=True, default="Hero Description")
    hero_primary_button_text = models.CharField(max_length=200, blank=True, default="Hero Primary Button Text")
    hero_primary_button_url = models.CharField(max_length=200, blank=True, help_text=LINK_HELP_TEXT)
    hero_secondary_button_text = models.CharField(max_length=200, blank=True, default="Hero Secondary Button Text")
    hero_secondary_button_url = models.CharField(max_length=200, blank=True, help_text=LINK_HELP_TEXT)

    # Welcome
    welcome_title = models.CharField(
        max_length=200,
        default="Welcome Title",
    )
    welcome_description = models.TextField(
        blank=True,
        default="Welcome Description",
    )
    welcome_button_text = models.CharField(
        max_length=200,
        default="Welcome Button Text",
    )
    welcome_button_url = models.CharField(
        max_length=200,
        blank=True,
        help_text=LINK_HELP_TEXT,
    )

    # Join CTA
    join_url = models.CharField(max_length=200, blank=True, help_text=LINK_HELP_TEXT)
    join_button_text = models.CharField(
        max_length=200,
        default="Join Today",
        blank=True,
    )

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        errors = {}
        for field_name in (
            "hero_primary_button_url",
            "hero_secondary_button_url",
            "welcome_button_url",
            "join_url",
        ):
            error = link_error(getattr(self, field_name))
            if error:
                errors[field_name] = error
        if errors:
            raise ValidationError(errors)

    # Properties
    @property
    def enabled_hero_images(self):
        return self.hero_images.filter(is_enabled=True)

    @property
    def enabled_navigation_items(self):
        return self.navigation_items.filter(is_enabled=True)

    @property
    def enabled_cards(self):
        return self.cards.filter(is_enabled=True)

    @property
    def enabled_info_panels(self):
        return self.info_panels.filter(is_enabled=True)

    @property
    def enabled_resources(self):
        return self.resources.filter(is_enabled=True)



class HeroImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hero_images"
    )
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to="hero/")
    is_enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=100)
    class Meta:
        ordering = ["order"]

class NavigationItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="navigation_items"
    )
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=200, help_text=LINK_HELP_TEXT)
    order = models.PositiveIntegerField(default=100)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "title"],
                name="unique_navigation_title_per_organization",
            ),
            models.UniqueConstraint(
                fields=["organization", "url"],
                name="unique_navigation_url_per_organization",
            )
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        error = link_error(self.url)
        if error:
            raise ValidationError({"url": error})


class Card(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="cards"
    )
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to="cards/", blank=True)
    icon = models.CharField(max_length=50, blank=True)
    link_text = models.CharField(max_length=200, blank=True)
    link = models.CharField(max_length=200, blank=True, help_text=LINK_HELP_TEXT)
    order = models.PositiveIntegerField(default=100)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        error = link_error(self.link)
        if error:
            raise ValidationError({"link": error})

class InfoPanel(models.Model):
    TYPE_STATIC = "static"
    TYPE_NEXT_MEETING = "next_meeting"

    TYPE_CHOICES = [
        (TYPE_STATIC, "Static"),
        (TYPE_NEXT_MEETING, "Next Meeting"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="info_panels"
    )
    panel_type = models.CharField(
        max_length=32,
        choices=TYPE_CHOICES,
        default=TYPE_STATIC,
    )

    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to="info_panels/", blank=True)
    icon = models.CharField(max_length=50, blank=True)
    link_text = models.CharField(max_length=200, blank=True)
    link = models.CharField(
        max_length=200,
        blank=True,
        help_text=LINK_HELP_TEXT + (
            ' Ignored for a "Next Meeting" panel - its link always '
            "points at whichever meeting is actually next."
        ),
    )
    order = models.PositiveIntegerField(default=100)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        # A "Next Meeting" panel's link is computed from whichever
        # meeting is actually next (see app/components/info_panel.html)
        # rather than taken from this field, so there's nothing to
        # validate here for that panel type.
        if self.panel_type == self.TYPE_NEXT_MEETING:
            return
        error = link_error(self.link)
        if error:
            raise ValidationError({"link": error})


class Resource(models.Model):
    """An admin-uploadable downloadable file - a scholarship application,
    a membership form, bylaws, etc. Public and unauthenticated, unlike
    meetings' agenda/minutes uploads (see meetings/storage.py), so it
    uses the default public MEDIA_ROOT storage rather than
    private_storage. Meant to back both one-off links (like the
    Scholarship page's application download) and the general
    /resources page once that's built out."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=300, blank=True)
    file = models.FileField(upload_to="resources/")
    order = models.PositiveIntegerField(default=100)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title
