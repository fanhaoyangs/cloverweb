from django.conf import settings
from django.db import models


class Topic(models.Model):
    NODE_CHOICES = [
        ('general', '综合讨论'),
        ('garden', '花园营造'),
        ('contest', '竞赛交流'),
        ('notice', '公告'),
    ]

    title = models.CharField('标题', max_length=200)
    content_html = models.TextField('正文 HTML', blank=True)
    node = models.CharField('板块', max_length=16, choices=NODE_CHOICES, default='general')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='topics', verbose_name='发帖人',
    )
    is_pinned = models.BooleanField('置顶', default=False)
    is_closed = models.BooleanField('锁定', default=False)
    view_count = models.PositiveIntegerField('浏览量', default=0)
    reply_count = models.PositiveIntegerField('回复数', default=0)
    last_reply_at = models.DateTimeField('最后回复时间', null=True, blank=True)
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
    content_html = models.TextField('回复 HTML', blank=True)
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
