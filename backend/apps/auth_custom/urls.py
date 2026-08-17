from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView

from .views import FeishuExchangeView, MeView, feishu_callback, feishu_login

urlpatterns = [
    path('feishu/login/', feishu_login),
    path('feishu/callback/', feishu_callback),
    path('feishu/exchange/', FeishuExchangeView.as_view()),
    # 账号密码换 JWT（dev 期 / superuser 后备用；正式 CMS 用飞书）
    path('token/', TokenObtainPairView.as_view()),
    path('me/', MeView.as_view()),
]
