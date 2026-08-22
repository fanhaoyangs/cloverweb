from django.contrib import admin

from .models import Like, Node, Post, Topic


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'order', 'is_active', 'staff_only', 'created_at')
    list_editable = ('order', 'is_active', 'staff_only')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'node', 'is_pinned', 'is_closed', 'reply_count', 'view_count', 'created_at')
    list_filter = ('node', 'is_pinned', 'is_closed')
    search_fields = ('title',)
    date_hierarchy = 'created_at'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('topic', 'author', 'created_at')
    search_fields = ('topic__title',)
    date_hierarchy = 'created_at'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'post', 'created_at')
