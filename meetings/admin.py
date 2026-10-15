from django.contrib import admin
from django.db import models
from django.utils import timezone

from core.models import Organization
from core.widgets import PrivateClearableFileInput
from meetings.models import Event, EventAttachment

# The admin's default file widget asks storage for the file's URL, which
# private storage refuses on purpose - without this, the edit page 500'd
# for any event with an agenda or minutes.
PRIVATE_FILE_WIDGET = {models.FileField: {"widget": PrivateClearableFileInput}}


class EventAttachmentInline(admin.TabularInline):
    model = EventAttachment
    extra = 0
    fields = ("title", "file", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    formfield_overrides = PRIVATE_FILE_WIDGET


class EventStatusFilter(admin.SimpleListFilter):
    title = "event status"
    parameter_name = "status"
    def lookups(self, request, model_admin):
        return (
            ("upcoming", "Upcoming"),
            ("past", "Past"),
        )

    def queryset(self, request, queryset):
        if self.value() == "upcoming":
            return queryset.filter(starts_at__gte=timezone.now())
        if self.value() == "past":
            return queryset.filter(starts_at__lt=timezone.now())
        return queryset

# Register your models here.
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    formfield_overrides = PRIVATE_FILE_WIDGET
    inlines = [EventAttachmentInline]
    list_display = (
        "title",
        "event_type",
        "starts_at",
        "location",
        "is_cancelled",
    )

    list_filter = (
        "event_type",
        EventStatusFilter,
        "is_cancelled",
    )

    ordering = (
        "starts_at",
    )

    def get_changeform_initial_data(self, request):
        # Single-org deployment for now (see architecture note in
        # core.middleware.organization) - default the org so adding an
        # event doesn't require picking it from a dropdown every time.
        initial = super().get_changeform_initial_data(request)
        organization = Organization.objects.first()
        if organization:
            initial.setdefault("organization", organization.pk)
        return initial
