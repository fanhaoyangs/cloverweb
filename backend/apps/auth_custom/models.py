from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """全站统一用户：CMS 内部（飞书 OAuth）+ BBS 公开用户（邮箱，Phase 3）。"""

    display_name = models.CharField('显示名', max_length=64, blank=True)
    avatar_url = models.URLField('头像 URL', blank=True)
    is_feishu_user = models.BooleanField('飞书登录用户', default=False)
    feishu_open_id = models.CharField('飞书 Open ID', max_length=64, blank=True, db_index=True)
    feishu_union_id = models.CharField('飞书 Union ID', max_length=64, blank=True)
    last_login_at = models.DateTimeField('最后登录时间', null=True, blank=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.display_name or self.username
