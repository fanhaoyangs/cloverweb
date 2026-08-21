"""CMS 管理 API 序列化器（需 is_staff）。"""
from rest_framework import serializers

from apps.content.models import Article, Category, Tag
from apps.team.models import SitePage


class CategoryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'order')
        read_only_fields = ('id',)
        extra_kwargs = {'slug': {'required': False}}


class ArticleAdminSerializer(serializers.ModelSerializer):
    """文章管理（可写）：category 传 slug，tags 传名称列表（不存在自动创建）。"""

    category = serializers.SlugRelatedField(
        slug_field='slug', queryset=Category.objects.all(),
        required=False, allow_null=True,
    )
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    tags = serializers.ListField(
        child=serializers.CharField(max_length=32), required=False, default=list,
        write_only=True,
    )
    author_name = serializers.CharField(source='author.display_name', read_only=True, default='')

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'excerpt', 'cover_image', 'content_html',
            'category', 'category_name', 'tags', 'status', 'is_featured',
            'website_sections', 'section_order', 'view_count',
            'author', 'author_name', 'published_at', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'view_count', 'author', 'published_at', 'created_at', 'updated_at')

    def validate_tags(self, value):
        return [v.strip() for v in value if v.strip()][:10]

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        validated_data['author'] = self.context['request'].user
        article = super().create(validated_data)
        self._sync_tags(article, tags)
        return article

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        article = super().update(instance, validated_data)
        if tags is not None:
            self._sync_tags(article, tags)
        return article

    @staticmethod
    def _sync_tags(article, names):
        from django.utils.text import slugify
        tag_objs = []
        for name in names:
            slug = slugify(name) or f'tag-{len(name)}-{ord(name[0])}'
            tag, _ = Tag.objects.get_or_create(name=name, defaults={'slug': slug[:32]})
            tag_objs.append(tag)
        article.tags.set(tag_objs)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # tags 为 write_only，响应中回填名称列表
        if instance.pk:
            data['tags'] = [t.name for t in instance.tags.all()]
        return data


# 系统保留地址：这些路径已有专属前端路由，页面用了会被路由吞掉无法访问
RESERVED_SLUGS = {'news', 'admin', 'login-callback'}


class SitePageAdminSerializer(serializers.ModelSerializer):
    """静态页管理（slug/title/content_html/status/菜单字段 可写）。"""

    class Meta:
        model = SitePage
        fields = (
            'slug', 'title', 'content_html', 'status',
            'in_menu', 'menu_label', 'menu_order',
            'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')
        extra_kwargs = {'slug': {'required': False}}

    def validate_slug(self, value):
        if value in RESERVED_SLUGS:
            raise serializers.ValidationError(f'「{value}」是系统保留地址，请换一个')
        return value
