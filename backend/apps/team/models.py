from django.conf import settings
from django.db import models


class TeamMember(models.Model):
    name = models.CharField('姓名', max_length=64)
    role = models.CharField('职务', max_length=128, blank=True)
    bio = models.TextField('简介', blank=True)
    avatar_url = models.URLField('头像 URL', blank=True)
    order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('在职/在册', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '团队成员'
        verbose_name_plural = '团队成员'
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class SitePage(models.Model):
    """静态内容页（迁移 main/ 的 index、clover、philosophy 三页），Vue 端 v-html 渲染。"""

    PAGE_CHOICES = [
        ('home', '首页'),
        ('about', '关于我们'),
        ('philosophy', '理念'),
    ]

    slug = models.SlugField('页面标识', max_length=32, unique=True, choices=PAGE_CHOICES)
    title = models.CharField('标题', max_length=200)
    content_html = models.TextField('内容 HTML', blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_pages', verbose_name='最后编辑人',
    )

    class Meta:
        verbose_name = '静态页'
        verbose_name_plural = '静态页'

    def __str__(self):
        return f'{self.get_slug_display()}（{self.slug}）'
