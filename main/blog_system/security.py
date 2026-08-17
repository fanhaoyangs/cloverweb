"""
安全模块
提供CSRF保护、XSS过滤、登录限制等安全功能
"""
from functools import wraps
from flask import request, jsonify, session, abort, g
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import safe_str_cmp
from datetime import datetime, timedelta
import hashlib
import hmac
import os
import re
from typing import Optional
import bleach
from models import LoginLog, User


class SecurityManager:
    """安全管理器"""
    
    def __init__(self, app=None):
        self.app = app
        self.csrf = None
        self.login_attempts = {}
        self.rate_limits = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化安全配置"""
        self.app = app
        self.csrf = CSRFProtect(app)
        
        # 配置bleach允许的HTML标签和属性
        self.allowed_tags = bleach.sanitizer.ALLOWED_TAGS + [
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'strong', 'em', 'u', 'del', 'ins',
            'ul', 'ol', 'li', 'blockquote',
            'pre', 'code',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img',
            'div', 'span',
            'br', 'hr',
            'figure', 'figcaption'
        ]
        
        self.allowed_attributes = {
            **bleach.sanitizer.ALLOWED_ATTRIBUTES,
            'img': ['src', 'alt', 'title', 'width', 'height', 'style', 'loading'],
            'a': ['href', 'title', 'target', 'rel'],
            'div': ['class', 'style', 'id'],
            'span': ['class', 'style', 'id'],
            'table': ['class', 'style', 'id'],
            'td': ['style', 'colspan', 'rowspan', 'id'],
            'th': ['style', 'colspan', 'rowspan', 'id'],
            'figure': ['class', 'id'],
            'figcaption': ['class', 'id'],
        }
        
        self.allowed_styles = [
            'max-width', 'width', 'height', 'border', 'margin', 'padding',
            'text-align', 'color', 'background-color', 'font-size', 'font-weight',
            'line-height', 'display', 'float', 'clear'
        ]
        
        self.allowed_protocols = ['http', 'https', 'mailto', 'tel']
    
    def sanitize_html(self, html: str) -> str:
        """HTML清理和XSS防护"""
        if not html:
            return ''
        
        # 使用bleach清理HTML
        cleaned = bleach.clean(
            html,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            styles=self.allowed_styles,
            protocols=self.allowed_protocols,
            strip=True
        )
        
        return cleaned
    
    def sanitize_markdown(self, markdown: str) -> str:
        """Markdown内容清理"""
        if not markdown:
            return ''
        
        # 移除危险的Markdown语法
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>',
            r'javascript:',
            r'on\w+\s*=',  # 事件处理程序
        ]
        
        for pattern in dangerous_patterns:
            markdown = re.sub(pattern, '', markdown, flags=re.IGNORECASE | re.DOTALL)
        
        return markdown
    
    def check_login_rate_limit(self, username: str, max_attempts: int = 5, 
                               lockout_minutes: int = 30) -> tuple:
        """
        检查登录频率限制
        
        Returns:
            (is_blocked, remaining_attempts, message)
        """
        now = datetime.now()
        key = f"login:{username}"
        
        # 获取或初始化登录尝试记录
        if key not in self.login_attempts:
            self.login_attempts[key] = {
                'count':0,
                'last_attempt': now,
                'blocked_until': None
            }
        
        record = self.login_attempts[key]
        
        # 检查是否被锁定
        if record['blocked_until'] and now < record['blocked_until']:
            remaining = (record['blocked_until'] - now).seconds // 60
            return True, 0, f"账号已锁定，请{remaining}分钟后重试"
        
        # 检查是否在锁定期间内
        if record['blocked_until'] and now >= record['blocked_until']:
            # 锁定已解除，重置计数器
            record['count'] = 0
            record['blocked_until'] = None
        
        remaining = max_attempts - record['count']
        
        if remaining <= 0:
            # 锁定账号
            record['blocked_until'] = now + timedelta(minutes=lockout_minutes)
            return True, 0, f"登录尝试次数过多，账号已锁定{lockout_minutes}分钟"
        
        return False, remaining, ""
    
    def record_login_attempt(self, username: str, success: bool, 
                            ip_address: str, user_agent: str):
        """记录登录尝试"""
        if success:
            # 登录成功，重置计数器
            key = f"login:{username}"
            if key in self.login_attempts:
                self.login_attempts[key] = {
                    'count': 0,
                    'last_attempt': datetime.now(),
                    'blocked_until': None
                }
        else:
            # 登录失败，增加计数器
            key = f"login:{username}"
            if key not in self.login_attempts:
                self.login_attempts[key] = {
                    'count': 0,
                    'last_attempt': datetime.now(),
                    'blocked_until': None
                }
            
            self.login_attempts[key]['count'] += 1
            self.login_attempts[key]['last_attempt'] = datetime.now()
    
    def generate_csrf_token(self) -> str:
        """生成CSRF令牌"""
        if self.csrf:
            return self.csrf.generate_csrf()
        return ''
    
    def validate_csrf_token(self, token: str) -> bool:
        """验证CSRF令牌"""
        if self.csrf:
            return self.csrf.validate_csrf(token)
        return False
    
    def get_client_ip(self) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or '0.0.0.0'
    
    def check_rate_limit(self, key: str, limit: int = 100, 
                         period: int = 3600) -> tuple:
        """
        检查请求频率限制
        
        Returns:
            (is_limited, remaining, reset_time)
        """
        now = datetime.now()
        
        if key not in self.rate_limits:
            self.rate_limits[key] = {
                'requests': [],
                'limit': limit
            }
        
        record = self.rate_limits[key]
        
        # 清理过期请求记录
        record['requests'] = [
            t for t in record['requests'] 
            if now - t < timedelta(seconds=period)
        ]
        
        current_count = len(record['requests'])
        
        if current_count >= limit:
            # 计算重置时间
            oldest = min(record['requests']) if record['requests'] else now
            reset_after = (oldest + timedelta(seconds=period)) - now
            return True, 0, int(reset_after.total_seconds())
        
        # 记录新请求
        record['requests'].append(now)
        
        remaining = limit - current_count - 1
        return False, remaining, period


# 创建全局安全管理器实例
security_manager = SecurityManager()


def require_rate_limit(key: str, limit: int = 100, period: int = 3600):
    """请求频率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            is_limited, remaining, reset_time = security_manager.check_rate_limit(
                key, limit, period
            )
            
            if is_limited:
                response = jsonify({
                    'code': 429,
                    'message': '请求过于频繁，请稍后再试',
                    'retry_after': reset_time
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(reset_time)
                return response
            
            # 添加速率限制头
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(reset_time)
            
            return response
        return decorated_function
    return decorator


def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """验证文件扩展名"""
    if not filename:
        return False
    
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    if not filename:
        return ''
    
    # 移除路径信息
    filename = os.path.basename(filename)
    
    # 移除特殊字符，只保留安全字符
    filename = re.sub(r'[^\w\-\.]', '', filename)
    
    # 限制长度
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename


def generate_secure_token(length: int = 32) -> str:
    """生成安全的随机令牌"""
    return hashlib.sha256(os.urandom(length)).hexdigest()


def hash_sensitive_data(data: str, key: str = None) -> str:
    """对敏感数据进行哈希处理"""
    if key is None:
        key = os.urandom(32)
    
    return hmac.new(
        key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def escape_html(text: str) -> str:
    """HTML转义"""
    if not text:
        return ''
    
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


class ContentSecurityPolicy:
    """内容安全策略配置"""
    
    @staticmethod
    def get_header() -> dict:
        """获取CSP响应头"""
        return {
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://fonts.gstatic.com; "
                "connect-src 'self' https://fonts.googleapis.com; "
                "frame-ancestors 'self'; "
                "form-action 'self'; "
                "base-uri 'self';"
            )
        }
    
    @staticmethod
    def get_nonce() -> str:
        """生成nonce值用于内联脚本"""
        import base64
        return base64.b64encode(os.urandom(16)).decode('utf-8')


def add_security_headers(response):
    """添加安全响应头"""
    # 安全相关头
    security_headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    }
    
    for header, value in security_headers.items():
        response.headers[header] = value
    
    # 添加CSP头
    csp_headers = ContentSecurityPolicy.get_header()
    for header, value in csp_headers.items():
        response.headers[header] = value
    
    return response
