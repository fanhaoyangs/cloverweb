"""飞书 OAuth 登录（仅 CMS 内部，v3.2 决策）。

流程（方案 v3.1 B3 修正，防 token 泄露）：
1. 前端 GET /api/auth/feishu/login/  → 拿 authorize_url（带一次性 state）
2. 用户在飞书授权 → 飞书回调 GET /api/auth/feishu/callback/?code=&state=
3. 后端校验 state、换用户信息、建/更新用户，生成 JWT，
   用一次性 exchange_code 重定向回前端 /login-callback?code=...
4. 前端 POST /api/auth/feishu/exchange/ {code} → 换 access JWT（一次性，120s）
"""
import secrets

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .feishu import get_user_access_token, get_user_info
from .models import User
from .serializers import UserSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def feishu_login(request):
    """第一步：生成带 state 的飞书授权链接。"""
    if not settings.FEISHU_APP_ID:
        return Response({'detail': '未配置 FEISHU_APP_ID'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    state = secrets.token_urlsafe(24)
    cache.set(f'feishu_state:{state}', True, timeout=300)
    url = (
        'https://open.feishu.cn/open-apis/authen/v1/authorize'
        f'?app_id={settings.FEISHU_APP_ID}'
        f'&redirect_uri={settings.FEISHU_REDIRECT_URI}'
        f'&state={state}'
    )
    return Response({'authorize_url': url})


@api_view(['GET'])
@permission_classes([AllowAny])
def feishu_callback(request):
    """第二步：飞书回跳。校验 state → 建用户 → 生成 JWT → 一次性 code 中转（不把 JWT 放 URL）。"""
    code = request.query_params.get('code', '')
    state = request.query_params.get('state', '')
    if not code or not cache.pop(f'feishu_state:{state}', False):
        return Response({'detail': 'state 无效或已过期，请重新发起登录'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token_data = get_user_access_token(code)
        user_info = get_user_info(token_data['access_token'])
    except Exception as exc:  # noqa: BLE001
        return Response({'detail': f'飞书授权失败: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

    open_id = user_info.get('open_id', '')
    # 白名单：配置了就只放白名单内账号（内部 CMS）
    if settings.FEISHU_ALLOWED_OPEN_IDS and open_id not in settings.FEISHU_ALLOWED_OPEN_IDS:
        return Response({'detail': '该飞书账号未在后台白名单内'}, status=status.HTTP_403_FORBIDDEN)

    user, _created = User.objects.get_or_create(
        username=f'feishu_{open_id[:12]}',
        defaults={
            'is_feishu_user': True,
            'feishu_open_id': open_id,
            'display_name': user_info.get('name', ''),
            'avatar_url': user_info.get('avatar_url', ''),
        },
    )
    user.is_feishu_user = True
    user.is_staff = True  # CMS 内部用户
    user.display_name = user_info.get('name') or user.display_name
    user.avatar_url = user_info.get('avatar_url') or user.avatar_url
    user.feishu_union_id = user_info.get('union_id') or user.feishu_union_id
    user.last_login_at = timezone.now()
    user.save()

    jwt = RefreshToken.for_user(user)
    exchange_code = secrets.token_urlsafe(24)
    # locmem 缓存存元组即可；将来换 Redis 时改为 JSON
    cache.set(f'feishu_exchange:{exchange_code}', (str(jwt.access_token), user.pk), timeout=120)
    return redirect(f'{settings.SITE_URL}/login-callback?code={exchange_code}')


class FeishuExchangeView(APIView):
    """第四步：前端用一次性 code 换 JWT。"""

    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get('code', '')
        cached = cache.get(f'feishu_exchange:{code}')
        if not cached:
            return Response({'detail': 'code 无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)
        cache.delete(f'feishu_exchange:{code}')
        access_token, user_pk = cached
        user = User.objects.get(pk=user_pk)
        return Response({'access': access_token, 'user': UserSerializer(user).data})


class MeView(APIView):
    """当前登录用户信息（JWT Bearer）。"""

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({'detail': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(UserSerializer(request.user).data)
