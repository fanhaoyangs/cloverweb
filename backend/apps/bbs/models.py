from django.conf import settings
from django.db import models


class Node(models.Model):
    """论坛板块：独立表（后台可增删），与文章分类体系解耦。

    seed_bbs_nodes 命令按 slug update_or_create 补默认板块。
    """

    slug = models.SlugField('标识', max_length=32, unique=True)
    name = models.CharField('名称', max_length=64)
    description = models.CharField('描述', max_length=255, blank=True)
    icon = models.CharField('图标（emoji）', max_length=16, blank=True)
    order = models.PositiveSmallIntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True)
    # 站务公告类板块仅管理员可发帖（回复不受限）
    staff_only = models.BooleanField('仅管理员发帖', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '论坛板块'
        verbose_name_plural = '论坛板块'
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class Topic(models.Model):
    title = models.CharField('标题', max_length=200)
    # 双份存储：md 供再编辑/纯文本场景，html 为服务端渲染+消毒后的展示版本
    content_md = models.TextField('正文 Markdown', blank=True)
    content_html = models.TextField('正文 HTML（服务端渲染）', blank=True)
    excerpt = models.CharField('摘要', max_length=200, blank=True)
    node = models.ForeignKey(
        Node, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='topics', verbose_name='板块',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='topics', verbose_name='发帖人',
    )
    is_pinned = models.BooleanField('置顶', default=False)
    is_closed = models.BooleanField('锁定', default=False)
    view_count = models.PositiveIntegerField('浏览量', default=0)
    reply_count = models.PositiveIntegerField('回复数', default=0)
    like_count = models.PositiveIntegerField('点赞数', default=0)
    last_reply_at = models.DateTimeField('最后回复时间', null=True, blank=True)
    last_reply_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='latest_replies', verbose_name='最后回复人',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '主题'
        verbose_name_plural = '主题'
        ordering = ['-is_pinned', '-last_reply_at', '-created_at']

    def __str__(self):
        return self.title


class Post(models.Model):
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name='replies', verbose_name='所属主题',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='posts', verbose_name='回复人',
    )
    content_md = models.TextField('回复 Markdown', blank=True)
    content_html = models.TextField('回复 HTML（服务端渲染）', blank=True)
    # 楼层号：2 起（楼主帖为 1 楼），创建时按 topic.reply_count 递增
    floor = models.PositiveIntegerField('楼层', default=0)
    like_count = models.PositiveIntegerField('点赞数', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '回复'
        verbose_name_plural = '回复'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.topic} 的回复 #{self.pk}'


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户',
    )
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, null=True, blank=True,
        related_name='likes', verbose_name='主题',
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, null=True, blank=True,
        related_name='likes', verbose_name='回复',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '点赞'
        verbose_name_plural = '点赞'
        constraints = [
            models.UniqueConstraint(fields=['user', 'topic'], name='uniq_like_topic'),
            models.UniqueConstraint(fields=['user', 'post'], name='uniq_like_post'),
        ]
