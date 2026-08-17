"""
配置文件
管理所有环境相关的配置信息
"""
import os
from datetime import timedelta

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')

# 加载.env文件（如果存在）
def load_env_file():
    """从.env文件加载环境变量"""
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()

# Flask配置
class FlaskConfig:
    """Flask应用配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI', 
        f'sqlite:///{os.path.join(BASE_DIR, "posts.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_DOMAIN = 'communitygarden.org.cn'
    
    # 确保重定向使用 HTTPS
    FORCE_HOST_FOR_REDIRECTS = 'communitygarden.org.cn'
    
    # 上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = UPLOAD_DIR
    
    # 时区配置
    TIMEZONE = 'Asia/Shanghai'


class COSConfig:
    """腾讯云COS配置"""
    # 从环境变量读取
    SECRET_ID = os.environ.get('COS_SECRET_ID', '')
    SECRET_KEY = os.environ.get('COS_SECRET_KEY', '')
    REGION = os.environ.get('COS_REGION', 'ap-shanghai')
    BUCKET_NAME = os.environ.get('COS_BUCKET_NAME', 'blog-images')
    CUSTOM_DOMAIN = os.environ.get('CUSTOM_DOMAIN', 'images.communitygarden.org.cn')
    
    # 允许的图片格式
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    # 图片存储路径模板
    IMAGE_PATH_TEMPLATE = 'images/{year}/{month:02d}/{day:02d}'


class SecurityConfig:
    """安全配置"""
    # 密码加密
    PASSWORD_HASH_METHOD = 'bcrypt'
    PASSWORD_ROUNDS = 12
    
    # CSRF配置
    WTF_CSRF_ENABLED = True
    
    # XSS防护
    XSS_ENABLED = True
    
    # 登录安全
    LOGIN_ATTEMPTS_MAX = 5
    LOGIN_LOCKOUT_MINUTES = 30


class SiteConfig:
    """站点配置"""
    SITE_NAME = '四叶草堂'
    SITE_URL = 'https://communitygarden.org.cn'
    SITE_DESCRIPTION = '四叶草堂社区花园 - 重塑家园 共生发展'
    
    # 分页配置
    POSTS_PER_PAGE = 12
    ADMIN_POSTS_PER_PAGE = 20
    
    # 文章配置
    EXCERPT_LENGTH = 200
    TITLE_MAX_LENGTH = 200


# 配置类字典
config = {
    'flask': FlaskConfig,
    'cos': COSConfig,
    'security': SecurityConfig,
    'site': SiteConfig
}


def get_config(name):
    """获取配置"""
    return config.get(name, FlaskConfig)()


# 初始化目录
def init_directories():
    """初始化必要的目录"""
    directories = [DATA_DIR, UPLOAD_DIR]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
