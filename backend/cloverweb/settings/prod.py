"""生产配置（CVM）：敏感项全部来自环境变量（systemd EnvironmentFile）。"""
import os

from .base import *  # noqa: F401,F403

DEBUG = False

# 生产必须显式提供 SECRET_KEY
assert os.getenv('DJANGO_SECRET_KEY'), '生产环境必须设置 DJANGO_SECRET_KEY'

ALLOWED_HOSTS = ['communitygarden.org.cn', 'www.communitygarden.org.cn']

# Nginx 做 HTTPS 终止，Django 在 127.0.0.1:8000
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
