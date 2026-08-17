"""
CloverWeb 基础配置（base）。
- 本地开发：cloverweb.settings.dev（SQLite）
- 生产（CVM）：cloverweb.settings.prod（PostgreSQL，env 提供敏感项）
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-key-change-me')
DEBUG = False

ALLOWED_HOSTS = ['.communitygarden.org.cn', 'localhost', '127.0.0.1']

# ---- 应用 ----
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 第三方
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # 本项目
    'apps.auth_custom',
    'apps.content',
    'apps.team',
    'apps.bbs',
    'apps.contest',
    'apps.common',
]

AUTH_USER_MODEL = 'auth_custom.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cloverweb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cloverweb.wsgi.application'

# ---- 数据库（prod 用 PostgreSQL；dev.py 覆盖为 SQLite）----
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'cloverweb'),
        'USER': os.getenv('DB_USER', 'cloverweb'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}

# ---- DRF / JWT ----
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.StandardPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---- CORS / CSRF ----
CORS_ALLOWED_ORIGINS = [
    'https://communitygarden.org.cn',
    'https://www.communitygarden.org.cn',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CSRF_TRUSTED_ORIGINS = [
    'https://communitygarden.org.cn',
    'https://www.communitygarden.org.cn',
]

# ---- 国际化 / 时区 ----
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# ---- 静态与媒体 ----
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---- 站点 ----
SITE_URL = os.getenv('SITE_URL', 'https://communitygarden.org.cn')

# ---- 飞书 OAuth（仅 CMS 内部登录，v3.2 决策）----
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID', '')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET', '')
FEISHU_REDIRECT_URI = os.getenv(
    'FEISHU_REDIRECT_URI',
    'https://communitygarden.org.cn/api/auth/feishu/callback/',
)
FEISHU_ALLOWED_OPEN_IDS = [
    x.strip() for x in os.getenv('FEISHU_ALLOWED_OPEN_IDS', '').split(',') if x.strip()
]

# ---- 腾讯云 COS（UEditorPlus 上传，Phase 2.1.4 启用）----
COS_SECRET_ID = os.getenv('COS_SECRET_ID', '')
COS_SECRET_KEY = os.getenv('COS_SECRET_KEY', '')
COS_REGION = os.getenv('COS_REGION', 'ap-shanghai')
COS_BUCKET = os.getenv('COS_BUCKET', '')
COS_BASE_URL = os.getenv('COS_BASE_URL', '')
