"""飞书文档导入 API（CMS 内部，user OAuth 模式）。

端点：
  GET  /api/admin/feishu/authorize/   获取带文档读取权限的授权链接（导入专用）
  GET  /api/admin/feishu/status/      配置状态 + 用户授权状态
  GET  /api/admin/feishu/documents/   文件夹文档列表（需配置 FEISHU_FOLDER_TOKEN）
  GET  /api/admin/feishu/history/     已导入文档记录
  GET  /api/admin/feishu/logs/        导入日志
  POST /api/admin/feishu/import/      粘贴链接导入 {url}，返回转换后 HTML

权限：AdminPermission（is_staff），JWT 认证。

说明：CMS 登录（/api/auth/feishu/login/）发起的授权不带文档 scope，
登录拿到的 user_access_token 无法读文档；导入前需通过 authorize/ 单独
授权一次（复用同一回调端点，回调会更新 FeishuToken）。
"""
import logging
import secrets
from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status as http
from rest_framework.response import Response
from rest_framework.views import APIView

from . import feishu_api
from .admin_views import AdminPermission
from .feishu_parser import FeishuDocParser
from .models import FeishuDocument, FeishuImportLog

logger = logging.getLogger(__name__)


class FeishuAuthorizeView(APIView):
    """生成带文档读取权限的飞书授权链接（导入文档专用，不侵入登录流程）。"""

    permission_classes = [AdminPermission]

    def get(self, request):
        if not settings.FEISHU_APP_ID:
            return Response({'detail': '未配置 FEISHU_APP_ID'}, status=http.HTTP_503_SERVICE_UNAVAILABLE)
        state = secrets.token_urlsafe(24)
        cache.set(f'feishu_state:{state}', True, timeout=300)
        url = (
            'https://open.feishu.cn/open-apis/authen/v1/authorize'
            f'?app_id={settings.FEISHU_APP_ID}'
            f'&redirect_uri={quote(settings.FEISHU_REDIRECT_URI, safe="")}'
            f'&state={state}'
            f'&scope={quote(feishu_api.IMPORT_SCOPES, safe="")}'
        )
        return Response({'authorize_url': url})


class FeishuStatusView(APIView):
    """飞书导入功能配置状态 + 用户授权状态。"""

    permission_classes = [AdminPermission]

    def get(self, request):
        # 已授权 = 存在 token 且授权范围包含文档读取权限（登录授权不含文档 scope，不算）
        authorized = False
        try:
            token_obj = request.user.feishu_token
            has_doc_scope = 'docx:document:readonly' in (token_obj.scope or '')
            now = timezone.now()
            access_alive = now < token_obj.expires_at - timezone.timedelta(seconds=300)
            refresh_alive = bool(token_obj.refresh_token) and (
                token_obj.refresh_expires_at is None or now < token_obj.refresh_expires_at
            )
            authorized = has_doc_scope and (access_alive or refresh_alive)
        except Exception:
            authorized = False

        return Response({
            'configured': bool(settings.FEISHU_APP_ID and settings.FEISHU_APP_SECRET),
            'authorized': authorized,
            'folder_enabled': bool(getattr(settings, 'FEISHU_FOLDER_TOKEN', '')),
        })


class FeishuDocumentsView(APIView):
    """文件夹文档列表（用户需有该文件夹访问权限）。"""

    permission_classes = [AdminPermission]

    def get(self, request):
        folder_token = getattr(settings, 'FEISHU_FOLDER_TOKEN', '')
        if not folder_token:
            return Response(
                {'detail': '未配置 FEISHU_FOLDER_TOKEN，请直接粘贴文档链接导入'},
                status=http.HTTP_400_BAD_REQUEST,
            )
        try:
            user_token = feishu_api.get_valid_user_token(request.user)
            data = feishu_api.list_folder_files(
                folder_token,
                user_token,
                page_token=request.query_params.get('page_token', ''),
            )
        except feishu_api.FeishuAuthRequired as exc:
            return Response({'detail': str(exc), 'need_auth': True}, status=http.HTTP_401_UNAUTHORIZED)
        except feishu_api.FeishuAPIError as exc:
            return Response({'detail': str(exc)}, status=http.HTTP_502_BAD_GATEWAY)
        files = [
            {
                'token': f.get('token', ''),
                'name': f.get('name', ''),
                'type': f.get('type', ''),
                'url': f.get('url', ''),
                'modified_time': f.get('modified_time', ''),
            }
            for f in data.get('files', [])
            if f.get('type') == 'docx'  # 仅新版文档可导入
        ]
        return Response({'files': files, 'page_token': data.get('page_token', ''), 'has_more': bool(data.get('has_more'))})


class FeishuImportView(APIView):
    """粘贴飞书文档链接导入：返回转换后的 UEditorPlus HTML（不直接落库为文章）。

    流程：解析链接 → 拉取元信息与 Block 树 → Block→HTML（图片转存 COS）
    → 记录 FeishuDocument / FeishuImportLog → 返回给前端注入编辑器。
    """

    permission_classes = [AdminPermission]

    def post(self, request):
        url = (request.data.get('url') or '').strip()
        if not url:
            return Response({'detail': '请提供飞书文档链接'}, status=http.HTTP_400_BAD_REQUEST)

        try:
            user_token = feishu_api.get_valid_user_token(request.user)
            parsed = feishu_api.parse_doc_url(url)
            meta = feishu_api.get_document_meta(parsed['doc_token'], user_token, parsed['source'])
            doc_token = meta['doc_token']
            blocks = feishu_api.get_document_blocks(doc_token, user_token, meta.get('revision_id', -1))
            # 图片下载也需要 user_token，通过闭包传入 parser
            result = FeishuDocParser(user_token=user_token).parse(blocks, title=meta.get('title', ''))
        except feishu_api.FeishuAuthRequired as exc:
            return Response({'detail': str(exc), 'need_auth': True}, status=http.HTTP_401_UNAUTHORIZED)
        except feishu_api.FeishuAPIError as exc:
            FeishuImportLog.objects.create(
                doc_token='', title='', status='failed',
                message=str(exc)[:2000], created_by=request.user,
            )
            return Response({'detail': str(exc)}, status=http.HTTP_502_BAD_GATEWAY)
        except Exception as exc:  # noqa: BLE001
            logger.exception('飞书导入失败')
            FeishuImportLog.objects.create(
                doc_token='', title='', status='failed',
                message=f'解析异常: {exc}'[:2000], created_by=request.user,
            )
            return Response({'detail': f'导入失败: {exc}'}, status=http.HTTP_500_INTERNAL_SERVER_ERROR)

        FeishuDocument.objects.update_or_create(
            doc_token=doc_token,
            defaults={'title': result['title'], 'source': parsed['source']},
        )
        FeishuImportLog.objects.create(
            doc_token=doc_token, title=result['title'], status='success',
            message='导入成功', image_count=result.get('image_count', 0),
            created_by=request.user,
        )
        return Response({
            'doc_token': doc_token,
            'title': result['title'],
            'html': result['html'],
            'image_count': result.get('image_count', 0),
            'image_failed': result.get('image_failed', 0),
        })


class FeishuHistoryView(APIView):
    """已导入的飞书文档记录（去重参考）。"""

    permission_classes = [AdminPermission]

    def get(self, request):
        docs = FeishuDocument.objects.select_related('article').order_by('-updated_at')[:50]
        return Response({'items': [
            {
                'doc_token': d.doc_token,
                'title': d.title,
                'source': d.source,
                'article_id': d.article_id,
                'last_sync_at': d.last_sync_at,
                'updated_at': d.updated_at,
            }
            for d in docs
        ]})


class FeishuLogsView(APIView):
    """导入操作日志（最近 50 条）。"""

    permission_classes = [AdminPermission]

    def get(self, request):
        logs = FeishuImportLog.objects.select_related('created_by').order_by('-created_at')[:50]
        return Response({'items': [
            {
                'doc_token': log.doc_token,
                'title': log.title,
                'status': log.status,
                'message': log.message,
                'image_count': log.image_count,
                'created_by': log.created_by.display_name if log.created_by else '',
                'created_at': log.created_at,
            }
            for log in logs
        ]})
