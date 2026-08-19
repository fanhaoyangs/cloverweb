"""飞书文档 API 封装（user_access_token 模式）。

设计决策（v1.1 方案修正）：
- 使用 user_access_token，用户通过 OAuth 授权后以用户身份访问文档
- 不需要将文档共享给应用，符合"用户导入自己的文档"的直觉
- 支持 docx 新版文档与 wiki 知识库链接（自动解析为 obj_token）
- 旧版 doc（/docs/ 链接）不支持，提示用户另存为 docx

所需飞书应用权限（后台开通）：
- docx:document:readonly  读取新版文档
- drive:drive:readonly     云空间文件列表 / 图片下载
- wiki:wiki:readonly       知识库节点解析
"""
import logging
import re

import requests
from django.conf import settings
from django.utils import timezone

from .models import FeishuToken

logger = logging.getLogger(__name__)

API_BASE_URL = 'https://open.feishu.cn'
# v3 令牌端点（获取/刷新 user_access_token，域名与 open.feishu.cn 不同）
TOKEN_URL = 'https://accounts.feishu.cn/oauth/v3/token'

# 文档导入所需授权范围：
# - offline_access          离线访问（飞书仅在包含此 scope 时返回 refresh_token）
# - docx:document:readonly  读取新版文档
# - drive:drive:readonly    云空间文件列表 / 图片下载
# - wiki:wiki:readonly      知识库节点解析
IMPORT_SCOPES = 'offline_access docx:document:readonly drive:drive:readonly wiki:wiki:readonly'

# token 失效/无权错误码（需重新授权）
_TOKEN_INVALID_CODES = (99991672, 99991661, 99991663)


class FeishuAPIError(Exception):
    """飞书 API 调用失败。"""


class FeishuAuthRequired(Exception):
    """用户需要重新授权飞书。"""


def get_valid_user_token(user) -> str:
    """获取有效的 user_access_token，过期则尝试刷新。

    返回可用的 token，若无法获取/刷新则抛出 FeishuAuthRequired。
    """
    try:
        token_obj = user.feishu_token
    except FeishuToken.DoesNotExist:
        raise FeishuAuthRequired('请先授权飞书以导入文档')

    # 提前 5 分钟视为过期
    if timezone.now() < token_obj.expires_at - timezone.timedelta(seconds=300):
        return token_obj.access_token

    # 尝试刷新（refresh_token 一次性：刷新成功会返回新的 refresh_token，必须立即保存）
    if not token_obj.refresh_token:
        raise FeishuAuthRequired('飞书授权已过期，请重新授权')

    resp = requests.post(
        TOKEN_URL,
        json={
            'grant_type': 'refresh_token',
            'client_id': settings.FEISHU_APP_ID,
            'client_secret': settings.FEISHU_APP_SECRET,
            'refresh_token': token_obj.refresh_token,
        },
        headers={'Content-Type': 'application/json; charset=utf-8'},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get('code') != 0:
        raise FeishuAuthRequired(
            f'飞书授权刷新失败，请重新授权: {data.get("error_description") or data.get("error") or data.get("msg")}'
        )

    expires_in = data.get('expires_in', 7200)
    refresh_expires_in = data.get('refresh_token_expires_in', 0)
    token_obj.access_token = data['access_token']
    token_obj.refresh_token = data.get('refresh_token') or token_obj.refresh_token
    token_obj.scope = data.get('scope') or token_obj.scope
    token_obj.expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
    if refresh_expires_in:
        token_obj.refresh_expires_at = timezone.now() + timezone.timedelta(seconds=refresh_expires_in)
    token_obj.save()
    return token_obj.access_token


def _headers(user_token: str) -> dict:
    return {
        'Authorization': f'Bearer {user_token}',
        'Content-Type': 'application/json',
    }


def _check(data: dict, action: str) -> dict:
    if data.get('code') != 0:
        msg = data.get('msg', '未知错误')
        if data.get('code') in _TOKEN_INVALID_CODES:
            raise FeishuAuthRequired(f'飞书授权已失效，请重新授权（{msg}）')
        raise FeishuAPIError(f'飞书{action}失败: {msg}')
    return data.get('data', {})


def resolve_wiki_node(wiki_token: str, user_token: str) -> tuple:
    """wiki 链接 token → (obj_token, obj_type)。obj_type 为 docx 时可导入。"""
    resp = requests.get(
        f'{API_BASE_URL}/open-apis/wiki/v2/spaces/get_node',
        params={'token': wiki_token},
        headers=_headers(user_token),
        timeout=10,
    )
    resp.raise_for_status()
    node = _check(resp.json(), '解析知识库节点').get('node', {})
    return node.get('obj_token', ''), node.get('obj_type', '')


def parse_doc_url(url_or_token: str) -> dict:
    """解析飞书文档链接或裸 token。

    返回 {'doc_token': str, 'source': 'docx'|'wiki'|'doc', 'url': str}
    """
    text = (url_or_token or '').strip()

    # 直接粘贴 token（无斜杠），默认按 docx 处理
    if '//' not in text and '/' not in text and text:
        return {'doc_token': text, 'source': 'docx', 'url': f'{API_BASE_URL}/docx/{text}'}

    # 飞书短链 https://xxx.feishu.cn/wiki/xxx / docx/xxx / docs/xxx
    m = re.search(r'/(wiki|docx|docs)/([A-Za-z0-9]+)', text)
    if not m:
        raise FeishuAPIError('无法识别的飞书文档链接，请粘贴 docx 或 wiki 链接')
    kind, token = m.group(1), m.group(2)
    if kind == 'docs':
        raise FeishuAPIError('旧版 doc 文档不支持导入，请在飞书中另存为新版 docx 后重试')
    return {'doc_token': token, 'source': kind, 'url': text.split('?')[0]}


def get_document_meta(doc_token: str, user_token: str, source: str = 'docx') -> dict:
    """文档元信息：{'title': str, 'revision_id': int}。wiki 链接先解析 obj_token。"""
    if source == 'wiki':
        doc_token, obj_type = resolve_wiki_node(doc_token, user_token)
        if obj_type and obj_type != 'docx':
            raise FeishuAPIError(f'知识库节点类型 {obj_type} 不支持导入（仅支持 docx）')
    resp = requests.get(
        f'{API_BASE_URL}/open-apis/docx/v1/documents/{doc_token}',
        headers=_headers(user_token),
        timeout=10,
    )
    resp.raise_for_status()
    doc = _check(resp.json(), '获取文档信息').get('document', {})
    return {'title': doc.get('title', ''), 'revision_id': doc.get('revision_id', -1), 'doc_token': doc_token}


def get_document_blocks(doc_token: str, user_token: str, revision_id: int = -1) -> list:
    """全量拉取文档 Block 列表（自动分页）。"""
    blocks, page_token = [], None
    while True:
        params = {'page_size': 500, 'document_revision_id': revision_id}
        if page_token:
            params['page_token'] = page_token
        resp = requests.get(
            f'{API_BASE_URL}/open-apis/docx/v1/documents/{doc_token}/blocks',
            params=params,
            headers=_headers(user_token),
            timeout=15,
        )
        resp.raise_for_status()
        data = _check(resp.json(), '获取文档内容')
        blocks.extend(data.get('items', []))
        page_token = data.get('page_token')
        if not data.get('has_more') or not page_token:
            break
    return blocks


def download_image(file_token: str, user_token: str) -> bytes:
    """下载飞书云文档图片（返回二进制内容）。"""
    resp = requests.get(
        f'{API_BASE_URL}/open-apis/drive/v1/medias/{file_token}/download',
        headers={'Authorization': f'Bearer {user_token}'},
        timeout=30,
    )
    if resp.status_code != 200:
        raise FeishuAPIError(f'下载飞书图片失败: HTTP {resp.status_code}')
    return resp.content


def list_folder_files(folder_token: str, user_token: str, page_size: int = 50, page_token: str = '') -> dict:
    """列出文件夹内容（用户需有该文件夹访问权限）。"""
    params = {'page_size': page_size}
    if folder_token:
        params['folder_token'] = folder_token
    if page_token:
        params['page_token'] = page_token
    resp = requests.get(
        f'{API_BASE_URL}/open-apis/drive/v1/files',
        params=params,
        headers=_headers(user_token),
        timeout=10,
    )
    resp.raise_for_status()
    return _check(resp.json(), '获取文件夹列表')
