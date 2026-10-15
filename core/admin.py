from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from core.models import HeroImage, Organization, NavigationItem, Card, Highlight, Officer, InfoPanel, Resource, ResourceCategory, ContactMessage, JoinRequest, User


class UserCreationAdminForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email",)


class UserChangeAdminForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


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
