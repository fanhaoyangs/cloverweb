from django.urls import path

from .views import FeishuExchangeView, MeView, feishu_callback, feishu_login

urlpatterns = [
    path('feishu/login/', feishu_login),
    path('feishu/callback/', feishu_callback),
    path('feishu/exchange/', FeishuExchangeView.as_view()),
    path('me/', MeView.as_view()),
]
