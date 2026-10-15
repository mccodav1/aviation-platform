import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.links import link_error
from core.permissions import OFFICER_GROUP_NAME
from core.storage import private_storage


class UserManager(BaseUserManager):
    """Manager for User, which logs in by email and has no username."""

    use_in_migrations = True

    def get_by_natural_key(self, email):
        # Login lookups ignore case - Pat@Example.com and pat@example.com
        # are the same account.
        return self.get(email__iexact=email)

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser must have is_staff and is_superuser set.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Site account. Logs in by email address - there is no username.
    Membership applicants get one created (inactive) when they apply;
    an officer approving the application activates it (see JoinRequest)."""

    username = None
    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Stored lowercase, so the unique constraint can't be dodged by
        # case and every lookup matches.
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.email

    @property
    def role(self):
        """The account tier, as officers think of it. Reads self.groups,
        so prefetch_related("groups") when listing many users."""
        if self.is_superuser:
            return "Superadmin"
        if any(group.name == OFFICER_GROUP_NAME for group in self.groups.all()):
            return "Officer"
        if self.is_staff:
            # Admin access but not in the officers group - unusual, so
            # it's called out rather than lumped in with officers.
            return "Staff"
        return "Member"

    @property
    def account_status(self):
        """Active, or why not: an applicant waiting on (or denied by)
        the review on /applications, or an account switched off."""
        if self.is_active:
            return "Active"
        join_request = getattr(self, "join_request", None)
        if join_request and join_request.is_pending:
            return "Pending approval"
        if join_request and join_request.is_denied:
            return "Denied"
        return "Inactive"

LINK_HELP_TEXT = (
    'Internal page: its URL name, e.g. "core:events". '
    'Uploaded file: "resource:<slug>" (see Resources - each one shows '
    'its own slug to reuse here). '
    'Off-site link: full address starting with "https://", "mailto:", '
    'or "tel:".'
)

# Kept to common document/image formats - also keeps FileResponse's
# content-type guessing (see resource_download in views.py) landing on
# safe, non-executable types for inline display. Mirrors, but doesn't
# import, meetings.models.ALLOWED_MEETING_FILE_EXTENSIONS - core must
# not depend on the optional meetings app.
ALLOWED_RESOURCE_FILE_EXTENSIONS = [
    "pdf", "doc", "docx", "odt", "rtf", "txt", "png", "jpg", "jpeg",
]


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
    # The headline ("Fly Together, Build Community.") is fixed markup in
    # app/home.html, not a DB field - it's brand copy that's expected to
    # change by editing the template/CSS directly for a given deployment,
    # not something an admin needs to retype at content-entry time.
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
    welcome_background_image = models.ImageField(upload_to="welcome/", blank=True)
    welcome_background_credit = models.CharField(
        max_length=200,
        blank=True,
        help_text="Small caption shown on the background image, e.g. \"Photo: Jasper Gray\" or a placeholder reminder."
    )

    # About
    about_background_image = models.ImageField(upload_to="about/", blank=True)

    # Join CTA
    join_url = models.CharField(max_length=200, blank=True, help_text=LINK_HELP_TEXT)
    join_button_text = models.CharField(
        max_length=200,
        default="Join Today",
        blank=True,
    )

    # Social - each footer icon only renders when its field is set (see
    # app/base.html), so an org with no Instagram presence just shows no
    # Instagram icon rather than a dead link.
    facebook_url = models.CharField(max_length=200, blank=True, help_text=LINK_HELP_TEXT)
    instagram_url = models.CharField(max_length=200, blank=True, help_text=LINK_HELP_TEXT)

    # Contact
    email = models.EmailField(
        blank=True,
        help_text="Public contact address shown on the Contact page.",
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
            "facebook_url",
            "instagram_url",
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
    def enabled_highlights(self):
        return self.highlights.filter(is_enabled=True)

    @property
    def enabled_officers(self):
        return self.officers.filter(is_enabled=True)

    @property
    def enabled_info_panels(self):
        return self.info_panels.filter(is_enabled=True)

    @property
    def enabled_resources(self):
        return self.resources.filter(is_enabled=True)

    @property
    def enabled_resource_categories(self):
        return self.resource_categories.filter(is_enabled=True)



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
    photo_credit = models.CharField(
        max_length=200,
        blank=True,
        help_text="Small caption shown on the image, e.g. \"Photo: Jasper Gray\" or a placeholder reminder."
    )
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

class Highlight(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="highlights"
    )
    icon = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=100)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

class Officer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="officers"
    )
    role = models.CharField(max_length=200)
    name = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(upload_to="officers/", blank=True)
    order = models.PositiveIntegerField(default=100)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "role"],
                name="unique_officer_role_per_organization",
            ),
        ]

    def __str__(self):
        return f"{self.role} ({self.name})" if self.name else self.role

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
    # No image field, unlike Card - an info panel is meant to render as a
    # small icon-led tile (see components/info_panel.html), and an
    # arbitrary photo doesn't fit that layout. Add it back deliberately
    # (with matching template/CSS work) if a future design calls for it,
    # rather than leaving an admin-editable field that nothing renders.
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


class ResourceCategory(models.Model):
    """A named grouping Resources are filed under - rendered as its own
    card on /resources. Officers can pick an existing one or type a new
    one when adding a Resource (see core/forms.py); there's no separate
    "manage categories" page since a category is only ever created
    alongside the first Resource that needs it."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="resource_categories",
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=100)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name_plural = "resource categories"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "title"],
                name="unique_resource_category_title_per_organization",
            ),
        ]

    def __str__(self):
        return self.title


class Resource(models.Model):
    """An uploadable downloadable file - a scholarship application, a
    membership form, bylaws, etc. Meant to back both one-off links (like
    the Scholarship page's application download) and the general
    /resources page.

    Every file lives in private storage (see core/storage.py) and is
    only ever served through resource_download (core/views.py), which
    checks `visibility` itself - VISIBILITY_PUBLIC is just "no login
    required," not "served as a raw public URL." That's what makes
    VISIBILITY_MEMBERS an actual access control rather than a cosmetic
    label: there's no public MEDIA_ROOT URL for any Resource file to
    leak in the first place, regardless of visibility.

    Every Resource also has a slug, so it can be linked to from any of
    this app's link fields (Card.link, InfoPanel.link, NavigationItem.
    url, Organization's button URLs) as "resource:<slug>" - see
    core/links.py - without writing a bespoke lookup for each new
    file."""

    VISIBILITY_PUBLIC = "public"
    VISIBILITY_MEMBERS = "members"

    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, "Public - anyone"),
        (VISIBILITY_MEMBERS, "Members - signed-in users only"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    category = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT,
        related_name="resources",
        help_text="Delete or reassign this category's other resources before deleting it.",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200,
        blank=True,
        help_text=(
            "Auto-filled from the title if left blank. Link to this file "
            'from anywhere on the site with "resource:<slug>".'
        ),
    )
    description = models.CharField(max_length=300, blank=True)
    file = models.FileField(
        upload_to="resources/",
        storage=private_storage,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_RESOURCE_FILE_EXTENSIONS)],
    )
    visibility = models.CharField(
        max_length=16,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
    )
    order = models.PositiveIntegerField(default=100)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_resource_slug_per_organization",
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_members_only(self):
        return self.visibility == self.VISIBILITY_MEMBERS

    def visible_to(self, user):
        return self.is_enabled and (
            self.visibility == self.VISIBILITY_PUBLIC
            or (user is not None and user.is_authenticated)
        )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "resource"
            candidate = base_slug
            suffix = 2
            while (
                Resource.objects
                .filter(organization=self.organization, slug=candidate)
                .exclude(pk=self.pk)
                .exists()
            ):
                candidate = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class SeenTracking(models.Model):
    """Shared "seen" status for things officers review (contact messages,
    join applications). Shared across officers: once any officer marks
    an item seen, it stops counting toward everyone's navbar badge."""

    seen_at = models.DateTimeField(null=True, blank=True)
    seen_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True

    def mark_seen(self, user):
        # A no-op if already seen, so it keeps whoever saw it first.
        if self.seen_at is None:
            self.seen_at = timezone.now()
            self.seen_by = user
            self.save(update_fields=["seen_at", "seen_by"])

    def mark_unseen(self):
        if self.seen_at is not None:
            self.seen_at = None
            self.seen_by = None
            self.save(update_fields=["seen_at", "seen_by"])


class ContactMessage(SeenTracking):
    """A message submitted through the Contact page's quick-message
    form. Always saved here regardless of whether email notification
    (see core/views.py) actually succeeds, so a submission is never
    lost to an unconfigured or temporarily-down mail server - officers
    can review everything in the admin either way."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="contact_messages",
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.created_at:%Y-%m-%d}"


class JoinRequest(SeenTracking):
    """A membership application submitted through the Join page.
    Applying also creates the applicant's account (see JoinRequestForm),
    inactive until an officer approves the application on /applications.
    Denied applications keep their inactive account, so a mistaken
    denial can still be approved."""

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_DENIED = "denied"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_DENIED, "Denied"),
    ]

    PILOT_STATUS_CHOICES = [
        ("enthusiast", "Not a pilot (yet) - just love aviation"),
        ("student", "Student pilot"),
        ("private", "Private pilot"),
        ("instrument", "Instrument rated"),
        ("commercial", "Commercial / ATP"),
        ("instructor", "Flight instructor (CFI)"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="join_requests",
    )
    # The account this application created. Kept nullable so the
    # application survives if the account is later deleted in /admin.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="join_request",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    pilot_status = models.CharField(max_length=20, choices=PILOT_STATUS_CHOICES)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.created_at:%Y-%m-%d}"

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    @property
    def is_decided(self):
        return not self.is_pending

    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

    @property
    def is_denied(self):
        return self.status == self.STATUS_DENIED

    def decide(self, status, officer):
        """Approve or deny. Approving activates the applicant's account
        (later this is also where the welcome packet gets sent); denying
        leaves it inactive. Deciding implies the application has been
        looked at, so it also clears it from the unseen badge."""
        self.status = status
        self.decided_at = timezone.now()
        self.decided_by = officer
        update_fields = ["status", "decided_at", "decided_by"]
        if self.seen_at is None:
            self.seen_at = self.decided_at
            self.seen_by = officer
            update_fields += ["seen_at", "seen_by"]
        self.save(update_fields=update_fields)

        if self.user and self.user.is_active != self.is_approved:
            self.user.is_active = self.is_approved
            self.user.save(update_fields=["is_active"])

    def delete_with_account(self):
        # A never-approved (inactive) account goes with its application,
        # freeing the email to apply again. An approved member's account
        # is never removed this way.
        user = self.user
        self.delete()
        if user and not user.is_active:
            user.delete()
