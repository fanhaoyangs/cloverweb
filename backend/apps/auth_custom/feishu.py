"""飞书（国内版 open.feishu.cn）OAuth 工具。沿用旧系统 main/blog_system/feishu_auth.py 的端点（方案 v3.1 A1 修正）。"""
import requests
from django.conf import settings

API_BASE_URL = 'https://open.feishu.cn'


def get_user_access_token(code: str) -> dict:
    """授权码换 user_access_token（OIDC）。"""
    resp = requests.post(
        f'{API_BASE_URL}/open-apis/authen/v1/oidc/access_token',
        json={
            'grant_type': 'authorization_code',
            'client_id': settings.FEISHU_APP_ID,
            'client_secret': settings.FEISHU_APP_SECRET,
            'code': code,
            'redirect_uri': settings.FEISHU_REDIRECT_URI,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get('code') != 0:
        raise RuntimeError(f'飞书换 token 失败: {data}')
    return data['data']


def get_user_info(user_access_token: str) -> dict:
    """用 user_access_token 拉用户信息（open_id / union_id / name / avatar_url）。"""
    resp = requests.get(
        f'{API_BASE_URL}/open-apis/authen/v1/user_info',
        headers={'Authorization': f'Bearer {user_access_token}'},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get('code') != 0:
        raise RuntimeError(f'飞书获取用户信息失败: {data}')
    return data['data']
