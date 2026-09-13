from django.contrib import admin

from core.models import HeroImage, Organization, NavigationItem, Card, InfoPanel, Resource


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

@admin.register(InfoPanel)
class InfoPanelAdmin(admin.ModelAdmin):
    pass

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'order', 'is_enabled')
    # Auto-fills the slug field from the title as you type, in-browser -
    # still editable before saving. Resource.save() is the fallback for
    # anything created outside the admin (a shell/data migration, say).
    prepopulated_fields = {'slug': ('title',)}