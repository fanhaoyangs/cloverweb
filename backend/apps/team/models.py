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
    """静态内容页，Vue 端 v-html 渲染。支持草稿/发布/撤下与导航菜单配置。"""

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已撤下'),
    ]

    slug = models.SlugField('页面标识', max_length=64, unique=True)
    title = models.CharField('标题', max_length=200)
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default='draft')
    content_html = models.TextField('内容 HTML', blank=True)
    in_menu = models.BooleanField('显示在导航', default=False)
    menu_label = models.CharField('菜单名称', max_length=64, blank=True)
    menu_order = models.IntegerField('菜单排序', default=0)
    # null=True 与 0003 迁移对齐（存量行加列时的兼容写法），新记录由 auto_now_add 填值
    created_at = models.DateTimeField('创建时间', auto_now_add=True, null=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_pages', verbose_name='最后编辑人',
    )

    class Meta:
        verbose_name = '静态页'
        verbose_name_plural = '静态页'
        ordering = ['menu_order', 'created_at', 'id']

    def __str__(self):
        return f'{self.menu_label or self.title or self.slug}（{self.slug}）'
