from django.contrib import admin

from .models import Article, Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'created_at')
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'is_featured', 'view_count', 'published_at')
    list_filter = ('status', 'category', 'is_featured')
    search_fields = ('title', 'slug')
    date_hierarchy = 'published_at'
    filter_horizontal = ('tags',)
    readonly_fields = ('view_count', 'created_at', 'updated_at')
