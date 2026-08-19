"""飞书（国内版）OAuth 工具。

令牌端点使用 v3（https://accounts.feishu.cn/oauth/v3/token，扁平响应），
授权链接沿用旧系统端点（open.feishu.cn/open-apis/authen/v1/authorize）。
"""
import requests
from django.conf import settings

API_BASE_URL = 'https://open.feishu.cn'
# v3 令牌端点：域名与 open.feishu.cn 不同，获取/刷新 user_access_token 共用
TOKEN_URL = 'https://accounts.feishu.cn/oauth/v3/token'


def get_user_access_token(code: str) -> dict:
    """授权码换 user_access_token（OAuth v3，响应为扁平结构）。"""
    resp = requests.post(
        TOKEN_URL,
        json={
            'grant_type': 'authorization_code',
            'client_id': settings.FEISHU_APP_ID,
            'client_secret': settings.FEISHU_APP_SECRET,
            'code': code,
            'redirect_uri': settings.FEISHU_REDIRECT_URI,
        },
        headers={'Content-Type': 'application/json; charset=utf-8'},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get('code') != 0:
        raise RuntimeError(f'飞书换 token 失败: {data.get("error_description") or data}')
    return data


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
