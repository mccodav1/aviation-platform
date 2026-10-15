from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group

from core.models import HeroImage, Organization, NavigationItem, Card, Highlight, Officer, InfoPanel, Resource, ResourceCategory, ContactMessage, JoinRequest, User
from core.permissions import GROUP_PERMISSIONS


class UserCreationAdminForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email",)


class UserChangeAdminForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def clean_is_active(self):
        # An applicant's account is switched on by approving their
        # application, not here - activating it directly would let them
        # in without an officer's decision and leave the application
        # still showing as pending (or denied).
        is_active = self.cleaned_data.get("is_active")
        join_request = getattr(self.instance, "join_request", None)
        if is_active and not self.instance.is_active and join_request and not join_request.is_approved:
            raise forms.ValidationError(
                "This account belongs to a membership application that hasn't been "
                "approved. Approve it on the Applications page instead."
            )
        return is_active


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Django's UserAdmin, minus the username - accounts log in by email.
    form = UserChangeAdminForm
    add_form = UserCreationAdminForm
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "usable_password", "password1", "password2"),
        }),
    )

    # Officers and Site Admins (change_user, but not superusers) manage
    # accounts without being able to escalate: no superuser status or individual
    # permissions, only the role groups, and no editing a superuser's
    # account (so not their password or active status either).

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser or obj is None:
            return fieldsets
        return tuple(
            (name, {**options, "fields": tuple(
                field for field in options["fields"]
                if field not in ("is_superuser", "user_permissions")
            )})
            for name, options in fieldsets
        )

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "groups" and not request.user.is_superuser:
            kwargs["queryset"] = Group.objects.filter(name__in=GROUP_PERMISSIONS)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(HeroImage)
class HeroImageAdmin(admin.ModelAdmin):
    pass

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    pass

@admin.register(NavigationItem)
class NavigationItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    pass

@admin.register(Highlight)
class HighlightAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_enabled')

@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ('role', 'name', 'order', 'is_enabled')

@admin.register(InfoPanel)
class InfoPanelAdmin(admin.ModelAdmin):
    pass

@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_enabled')

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'visibility', 'slug', 'order', 'is_enabled')
    list_filter = ('category', 'visibility', 'is_enabled')
    # Auto-fills the slug field from the title as you type, in-browser -
    # still editable before saving. Resource.save() is the fallback for
    # anything created outside the admin (a shell/data migration, say).
    prepopulated_fields = {'slug': ('title',)}

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'seen_at', 'seen_by')
    readonly_fields = ('name', 'email', 'message', 'created_at', 'seen_at', 'seen_by')
    ordering = ('-created_at',)

@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'pilot_status', 'status', 'created_at', 'seen_at')
    list_filter = ('status', 'pilot_status')
    # All read-only: approve/deny happens on /applications, which also
    # activates or deactivates the linked account - editing status here
    # would leave the two out of step.
    readonly_fields = (
        'user', 'first_name', 'last_name', 'email', 'phone', 'pilot_status', 'message',
        'created_at', 'status', 'seen_at', 'seen_by', 'decided_at', 'decided_by',
    )
    ordering = ('-created_at',)
