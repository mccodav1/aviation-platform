from django.contrib import admin
from django.utils import timezone

from core.models import Organization
from meetings.models import Meeting

class MeetingStatusFilter(admin.SimpleListFilter):
    title = "meeting status"
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
@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "starts_at",
        "location",
        "is_cancelled",
    )

    list_filter = (
        MeetingStatusFilter,
        "is_cancelled",
    )

    ordering = (
        "starts_at",
    )

    def get_changeform_initial_data(self, request):
        # Single-org deployment for now (see architecture note in
        # core.middleware.organization) - default the org so adding a
        # meeting doesn't require picking it from a dropdown every time.
        initial = super().get_changeform_initial_data(request)
        organization = Organization.objects.first()
        if organization:
            initial.setdefault("organization", organization.pk)
        return initial
