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


class FeishuToken(models.Model):
    """飞书 user_access_token 持久化（文档导入用，与 CMS 登录解耦）。

    用户在 CMS 登录后，若需要导入飞书文档，需额外完成一次 OAuth 授权，
    此处存储该用户的 user_access_token / refresh_token 及过期时间。
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='feishu_token', verbose_name='用户',
    )
    access_token = models.TextField('user_access_token')
    refresh_token = models.TextField('refresh_token', blank=True)
    # 授权范围（空格分隔）。仅当包含文档读取权限时才可用于文档导入
    scope = models.TextField('授权范围', blank=True)
    expires_at = models.DateTimeField('access_token 过期时间')
    # refresh_token 过期时间（飞书授权有效期上限 365 天，超期须重新授权）
    refresh_expires_at = models.DateTimeField('refresh_token 过期时间', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '飞书用户令牌'
        verbose_name_plural = '飞书用户令牌'

    def __str__(self):
        return f'FeishuToken({self.user_id})'


class FeishuDocument(models.Model):
    """飞书文档导入记录（user OAuth 模式）。"""
    doc_token = models.CharField('飞书文档 Token', max_length=128, unique=True, db_index=True)
    title = models.CharField('文档标题', max_length=300)
    source = models.CharField('链接类型', max_length=16, default='docx')  # docx / wiki
    article = models.ForeignKey(
        Article, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='feishu_docs', verbose_name='关联文章',
    )
    last_sync_at = models.DateTimeField('最后同步时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '飞书文档'
        verbose_name_plural = '飞书文档'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.title} ({self.doc_token[:16]})'


class FeishuImportLog(models.Model):
    """飞书导入操作日志。"""
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
    ]
    doc_token = models.CharField(max_length=128, db_index=True)
    title = models.CharField('文档标题', max_length=300, blank=True)
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES)
    message = models.TextField('说明', blank=True)
    image_count = models.IntegerField('转存图片数', default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='feishu_import_logs', verbose_name='操作人',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '飞书导入日志'
        verbose_name_plural = '飞书导入日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title or self.doc_token[:16]} - {self.status}'
