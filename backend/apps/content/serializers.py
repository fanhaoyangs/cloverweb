from rest_framework import serializers

from apps.content.models import Article, Category, Tag
from apps.team.models import SitePage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class ArticleListSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    tags = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'excerpt', 'cover_image', 'category', 'tags',
            'view_count', 'is_featured', 'website_sections', 'section_order', 'published_at',
        )


class ArticleDetailSerializer(ArticleListSerializer):
    author_name = serializers.CharField(source='author.display_name', read_only=True, default='')

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + ('content_html', 'author_name', 'created_at', 'updated_at')


class SitePageSerializer(serializers.ModelSerializer):
    """静态页（前台详情 / 导航列表共用）。"""

    class Meta:
        model = SitePage
        fields = ('slug', 'title', 'menu_label', 'menu_order', 'content_html', 'updated_at')


class SitePageMenuSerializer(serializers.ModelSerializer):
    """导航菜单精简版：不含 content_html（列表接口避免传输整页 HTML）。"""

    class Meta:
        model = SitePage
        fields = ('slug', 'title', 'menu_label', 'menu_order')
