from django.contrib import admin

from core.models import HeroImage, Organization, NavigationItem, Card, Highlight, Officer, InfoPanel, Resource, ResourceCategory, ContactMessage, JoinRequest


# Register your models here.
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
    list_display = ('name', 'email', 'pilot_status', 'status', 'created_at', 'seen_at')
    list_filter = ('status', 'pilot_status')
    # status stays editable - it's where a decision gets changed after
    # the fact (the Applications page only decides pending ones).
    readonly_fields = (
        'name', 'email', 'phone', 'pilot_status', 'message', 'created_at',
        'seen_at', 'seen_by', 'decided_at', 'decided_by',
    )
    ordering = ('-created_at',)
