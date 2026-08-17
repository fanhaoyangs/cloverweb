from django.contrib import admin

from .models import SitePage, TeamMember


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'role')


@admin.register(SitePage)
class SitePageAdmin(admin.ModelAdmin):
    list_display = ('slug', 'title', 'updated_at', 'updated_by')
    search_fields = ('slug', 'title')
    readonly_fields = ('updated_at',)
