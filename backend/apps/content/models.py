from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField('名称', max_length=64)
    slug = models.SlugField('标识', max_length=64, unique=True)
    description = models.CharField('描述', max_length=255, blank=True)
    order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '文章分类'
        verbose_name_plural = '文章分类'
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField('名称', max_length=32)
    slug = models.SlugField('标识', max_length=32, unique=True)

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'

    def __str__(self):
        return self.name


class Article(models.Model):
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]

    title = models.CharField('标题', max_length=200)
    slug = models.SlugField('URL 标识', max_length=200, unique=True)
    excerpt = models.CharField('摘要', max_length=500, blank=True)
    cover_image = models.URLField('封面图 URL', blank=True)
    content_html = models.TextField('正文 HTML（UEditorPlus）', blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles', verbose_name='分类',
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles', verbose_name='标签')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles', verbose_name='作者',
    )
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField('首页精选', default=False)
    view_count = models.PositiveIntegerField('浏览量', default=0)
    # 首页板块挂载：如 ['home_hero', 'home_news']（对应 HomePage.vue 的卡片位）
    website_sections = models.JSONField('首页板块', default=list, blank=True)
    section_order = models.IntegerField('板块内排序', default=0)
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', '-published_at']),
        ]

    def save(self, *args, **kwargs):
        if self.status == 'published' and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
