from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CloverUserAdmin(UserAdmin):
    list_display = ('username', 'display_name', 'email', 'is_feishu_user', 'is_staff', 'last_login_at')
    search_fields = ('username', 'display_name', 'email', 'feishu_open_id')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_feishu_user')
    fieldsets = UserAdmin.fieldsets + (
        ('扩展信息', {
            'fields': ('display_name', 'avatar_url', 'is_feishu_user', 'feishu_open_id', 'feishu_union_id', 'last_login_at'),
        }),
    )
    readonly_fields = ('last_login_at', 'feishu_open_id', 'feishu_union_id')
