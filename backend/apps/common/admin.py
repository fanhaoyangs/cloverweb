from django.contrib import admin

from .models import SiteConfig, UploadedFile


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'updated_at', 'updated_by')
    search_fields = ('key',)


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'size', 'uploaded_by', 'created_at')
    search_fields = ('original_name',)
    readonly_fields = ('file_url', 'original_name', 'size', 'uploaded_by', 'created_at')
    date_hierarchy = 'created_at'
