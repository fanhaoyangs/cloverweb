from django.conf import settings
from django.db import models


class SiteConfig(models.Model):
    """站点键值配置（页脚文案、联系方式等），value 存 JSON。"""

    key = models.CharField('键', max_length=64, unique=True)
    value = models.JSONField('值', default=dict)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='最后编辑人',
    )

    class Meta:
        verbose_name = '站点配置'
        verbose_name_plural = '站点配置'

    def __str__(self):
        return self.key


class UploadedFile(models.Model):
    """UEditorPlus 上传记录（文件本体存 COS）。"""

    file_url = models.URLField('文件 URL')
    original_name = models.CharField('原始文件名', max_length=255, blank=True)
    size = models.PositiveIntegerField('大小（字节）', default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='上传人',
    )
    created_at = models.DateTimeField('上传时间', auto_now_add=True)

    class Meta:
        verbose_name = '上传文件'
        verbose_name_plural = '上传文件'
        ordering = ['-created_at']

    def __str__(self):
        return self.original_name or self.file_url
