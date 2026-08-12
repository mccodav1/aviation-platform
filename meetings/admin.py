from django.contrib import admin
from django.utils import timezone
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
