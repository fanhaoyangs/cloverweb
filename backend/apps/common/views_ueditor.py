"""UEditorPlus 后端接口（统一入口 /api/ueditor/）。

按 UEditor 标准协议根据 ?action= 分发：
  config       -> 编辑器配置 JSON
  uploadimage  -> 图片上传（form-data 字段 upfile）
  uploadvideo  -> 视频上传
  uploadfile   -> 附件上传
  catchimage   -> 远程图片抓取转存（source[] 数组）
  listimage    -> 已上传图片列表（UploadedFile 表）

文件本体存腾讯云 COS（apps.common.cos），记录入 UploadedFile。
"""
import logging
import os
from urllib.parse import urlparse

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import cos
from .models import UploadedFile

logger = logging.getLogger(__name__)

# ---- 类型规则 ----
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
VIDEO_EXTS = {'.mp4', '.webm', '.flv', '.ogg', '.mov'}
FILE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.mp4', '.webm',
             '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar'}
IMAGE_MAX_SIZE = 20 * 1024 * 1024   # 20MB
VIDEO_MAX_SIZE = 200 * 1024 * 1024  # 200MB
FILE_MAX_SIZE = 50 * 1024 * 1024    # 50MB

MIME_BY_EXT = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'gif': 'image/gif', 'bmp': 'image/bmp', 'webp': 'image/webp',
    'mp4': 'video/mp4', 'webm': 'video/webm', 'flv': 'video/x-flv',
    'ogg': 'video/ogg', 'mov': 'video/quicktime',
    'pdf': 'application/pdf', 'zip': 'application/zip', 'rar': 'application/x-rar-compressed',
}

UEDITOR_CONFIG = {
    # 图片上传
    'imageActionName': 'uploadimage',
    'imageFieldName': 'upfile',
    'imageMaxSize': IMAGE_MAX_SIZE,
    'imageAllowFiles': sorted(IMAGE_EXTS),
    'imageCompressEnable': True,
    'imageCompressBorder': 1600,
    'imageInsertAlign': 'none',
    'imageUrlPrefix': '',
    'imagePathFormat': 'ueditor/images/{yyyy}{mm}{dd}/{time}{rand:6}',
    # 远程图片抓取（秀米等）
    'catcherActionName': 'catchimage',
    'catcherFieldName': 'source',
    'catcherMaxSize': IMAGE_MAX_SIZE,
    'catcherAllowFiles': sorted(IMAGE_EXTS),
    'catcherUrlPrefix': '',
    # 视频上传
    'videoActionName': 'uploadvideo',
    'videoFieldName': 'upfile',
    'videoMaxSize': VIDEO_MAX_SIZE,
    'videoAllowFiles': sorted(VIDEO_EXTS),
    'videoUrlPrefix': '',
    # 附件上传
    'fileActionName': 'uploadfile',
    'fileFieldName': 'upfile',
    'fileMaxSize': FILE_MAX_SIZE,
    'fileAllowFiles': sorted(FILE_EXTS),
    'fileUrlPrefix': '',
    # 在线图片管理
    'imageManagerActionName': 'listimage',
    'imageManagerListSize': 20,
    'imageManagerUrlPrefix': '',
    'imageManagerInsertAlign': 'none',
    # 在线文件管理（暂未实现，返回空列表）
    'fileManagerActionName': 'listfile',
    'fileManagerListSize': 20,
    'fileManagerUrlPrefix': '',
}


def _fail(message):
    return JsonResponse({'state': 'FAIL', 'message': message})


def _guess_mime(filename, fallback='application/octet-stream'):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return MIME_BY_EXT.get(ext, fallback)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def ueditor_entry(request):
    """UEditor 统一入口。权限：暂与旧系统一致允许匿名（CMS 飞书登录上线后收紧）。"""
    action = request.GET.get('action', '')
    handler = {
        'config': handle_config,
        'uploadimage': handle_upload,
        'uploadvideo': handle_upload,
        'uploadfile': handle_upload,
        'catchimage': handle_catchimage,
        'listimage': handle_listimage,
        'listfile': handle_listfile,
    }.get(action)
    if not handler:
        return _fail(f'不支持的操作: {action}')
    return handler(request)


def handle_config(request):
    return JsonResponse(UEDITOR_CONFIG)


def handle_upload(request):
    """图片 / 视频 / 附件上传（form-data，字段名 upfile）。"""
    file = request.FILES.get('upfile')
    if not file:
        return _fail('没有上传文件')

    action = request.GET.get('action')
    if action == 'uploadimage':
        allowed_exts, max_size, prefix = IMAGE_EXTS, IMAGE_MAX_SIZE, 'images'
    elif action == 'uploadvideo':
        allowed_exts, max_size, prefix = VIDEO_EXTS, VIDEO_MAX_SIZE, 'videos'
    else:
        allowed_exts, max_size, prefix = FILE_EXTS, FILE_MAX_SIZE, 'files'

    original_name = file.name or 'upload'
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in allowed_exts:
        return _fail(f'不支持的文件类型: {ext or "(无扩展名)"}')
    if file.size > max_size:
        limit_mb = max_size // (1024 * 1024)
        return _fail(f'文件大小超过限制（最大 {limit_mb}MB）')

    try:
        key = cos.build_object_key(prefix, ext)
        url = cos.upload_bytes(key, file.read(), _guess_mime(original_name))
    except cos.CosNotConfigured as e:
        return _fail(str(e))
    except Exception as e:
        logger.exception('UEditor 上传失败')
        return _fail(f'上传失败: {e}')

    UploadedFile.objects.create(
        file_url=url,
        original_name=original_name[:255],
        size=file.size,
        uploaded_by=request.user if request.user.is_authenticated else None,
    )
    return JsonResponse({'state': 'SUCCESS', 'url': url, 'title': original_name, 'original': original_name})


def handle_catchimage(request):
    """远程图片抓取转存 COS（source[] 数组，一次可传多个）。"""
    sources = request.POST.getlist('source[]') or request.GET.getlist('source[]')
    # UEditorPlus 部分版本用 source 字段名
    sources = sources or request.POST.getlist('source') or request.GET.getlist('source')
    if not sources:
        return _fail('没有提供远程图片 URL')

    results = []
    for remote in sources:
        item = _catch_one(remote)
        if item:
            results.append(item)
    if not results:
        return _fail('远程图片抓取失败（全部失败或格式不支持）')
    return JsonResponse({'state': 'SUCCESS', 'list': results})


def _catch_one(remote_url):
    """下载单张远程图片并转存 COS。失败返回 None。"""
    parsed = urlparse(remote_url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return None
    name = os.path.basename(parsed.path) or 'remote.jpg'
    ext = os.path.splitext(name)[1].lower()
    if ext not in IMAGE_EXTS:
        # 无扩展名或不在白名单时按 jpg 处理（秀米图常无扩展名）
        ext, name = '.jpg', name + '.jpg'
    try:
        resp = requests.get(remote_url, timeout=20, headers={'User-Agent': 'Mozilla/5.0 CloverWeb'})
        resp.raise_for_status()
        data = resp.content
        if len(data) > IMAGE_MAX_SIZE:
            return None
        key = cos.build_object_key('images', ext)
        url = cos.upload_bytes(key, data, _guess_mime(name))
    except Exception:
        logger.warning('UEditor 远程图片抓取失败: %s', remote_url, exc_info=True)
        return None
    UploadedFile.objects.create(
        file_url=url,
        original_name=name[:255],
        size=len(data),
        uploaded_by=None,
    )
    return {'url': url, 'source': remote_url, 'title': name}


def handle_listimage(request):
    """在线图片列表（UploadedFile 表，倒序分页）。"""
    return _list_files(request, 'images/')


def handle_listfile(request):
    """在线文件列表（暂返回空，前端媒体库后续接 UploadedFile 全量）。"""
    return _list_files(request, '')


def _list_files(request, key_prefix):
    try:
        start = max(int(request.GET.get('start', 0)), 0)
        size = min(max(int(request.GET.get('size', 20)), 1), 100)
    except ValueError:
        start, size = 0, 20

    qs = UploadedFile.objects.order_by('-created_at')
    if key_prefix:
        qs = qs.filter(file_url__contains=f'/{key_prefix}')
    total = qs.count()
    items = [
        {'url': f.file_url, 'title': f.original_name, 'original': f.original_name, 'mtime': int(f.created_at.timestamp())}
        for f in qs[start:start + size]
    ]
    return JsonResponse({'state': 'SUCCESS', 'list': items, 'start': start, 'total': total})
