"""腾讯云 COS 上传工具（UEditorPlus 编辑器媒体文件）。

凭证从环境变量 / backend/.env 读取：
  COS_SECRET_ID / COS_SECRET_KEY / COS_REGION / COS_BUCKET / COS_BASE_URL
"""
import random
import time
from datetime import datetime

from django.conf import settings
from qcloud_cos import CosConfig, CosS3Client


class CosNotConfigured(Exception):
    """COS 凭证未配置。"""


def get_cos_client() -> CosS3Client:
    if not (settings.COS_SECRET_ID and settings.COS_SECRET_KEY and settings.COS_BUCKET):
        raise CosNotConfigured(
            'COS 未配置：请在 backend/.env 设置 COS_SECRET_ID / COS_SECRET_KEY / COS_BUCKET'
        )
    config = CosConfig(
        Region=settings.COS_REGION,
        SecretId=settings.COS_SECRET_ID,
        SecretKey=settings.COS_SECRET_KEY,
        Scheme='https',
    )
    return CosS3Client(config)


def build_object_key(prefix: str, ext: str) -> str:
    """生成对象键：ueditor/<prefix>/<yyyymmdd>/<time><rand>.<ext>（与旧系统路径规则一致）。"""
    now = datetime.now()
    stamp = int(time.time() * 1000)
    rand = f'{random.randint(0, 999999):06d}'
    ext = ext.lower().lstrip('.') or 'bin'
    return f'ueditor/{prefix}/{now:%Y%m%d}/{stamp}{rand}.{ext}'


def public_url(key: str) -> str:
    base = (settings.COS_BASE_URL or '').rstrip('/')
    return f'{base}/{key}'


def upload_bytes(key: str, data: bytes, content_type: str) -> str:
    """上传字节流到 COS，返回 CDN 公网 URL。"""
    client = get_cos_client()
    client.put_object(
        Bucket=settings.COS_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return public_url(key)
