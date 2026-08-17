"""
安全模块测试
"""
import pytest
from flask import Flask
from security import (
    SecurityManager, 
    sanitize_filename, 
    generate_secure_token,
    escape_html,
    validate_file_extension
)
from werkzeug.security import generate_password_hash, check_password_hash


@pytest.fixture
def app():
    """创建测试应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    security = SecurityManager()
    security.init_app(app)
    
    yield app


@pytest.fixture
def security_manager(app):
    """创建安全管理器实例"""
    return SecurityManager(app)


class TestSecurityManager:
    """安全管理器测试类"""
    
    def test_sanitize_html_basic(self, security_manager):
        """测试HTML基本清理"""
        # 正常HTML应该保留
        html = '<p>Hello World</p>'
        result = security_manager.sanitize_html(html)
        assert '<p>Hello World</p>' in result
        
        # 危险标签应该被移除
        html = '<script>alert("xss")</script>'
        result = security_manager.sanitize_html(html)
        assert '<script>' not in result
        assert 'alert' not in result
    
    def test_sanitize_html_xss_prevention(self, security_manager):
        """测试XSS防护"""
        # 事件处理程序应该被移除
        html = '<img src=x onerror=alert(1)>'
        result = security_manager.sanitize_html(html)
        assert 'onerror' not in result
        
        # JavaScript协议应该被移除
        html = '<a href="javascript:alert(1)">Click</a>'
        result = security_manager.sanitize_html(html)
        assert 'javascript:' not in result
    
    def test_sanitize_markdown(self, security_manager):
        """测试Markdown清理"""
        # 正常Markdown应该保留
        md = '**bold** *italic*'
        result = security_manager.sanitize_markdown(md)
        assert '**bold**' in result
        assert '*italic*' in result
        
        # 危险内容应该被移除
        md = '<script>alert(1)</script>'
        result = security_manager.sanitize_markdown(md)
        assert '<script>' not in result
    
    def test_login_rate_limit(self, security_manager):
        """测试登录频率限制"""
        username = 'testuser'
        
        # 首次尝试应该允许
        is_blocked, remaining, _ = security_manager.check_login_rate_limit(
            username, max_attempts=3, lockout_minutes=1
        )
        assert is_blocked == False
        assert remaining == 3
        
        # 多次失败尝试
        for _ in range(3):
            security_manager.record_login_attempt(username, False, '127.0.0.1', 'test')
        
        is_blocked, remaining, _ = security_manager.check_login_rate_limit(
            username, max_attempts=3, lockout_minutes=1
        )
        assert is_blocked == True
        assert remaining == 0
    
    def test_login_success_resets_attempts(self, security_manager):
        """测试登录成功后重置尝试次数"""
        username = 'testuser'
        
        # 多次失败
        for _ in range(2):
            security_manager.record_login_attempt(username, False, '127.0.0.1', 'test')
        
        # 登录成功
        security_manager.record_login_attempt(username, True, '127.0.0.1', 'test')
        
        # 应该重置
        is_blocked, remaining, _ = security_manager.check_login_rate_limit(
            username, max_attempts=3, lockout_minutes=1
        )
        assert is_blocked == False
        assert remaining == 3


class TestUtilityFunctions:
    """工具函数测试类"""
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        # 正常文件名
        assert sanitize_filename('image.jpg') == 'image.jpg'
        assert sanitize_filename('my-document.pdf') == 'my-document.pdf'
        
        # 危险字符应该被移除
        assert sanitize_filename('../../etc/passwd') != 'etc/passwd'
        assert sanitize_filename('file<script>.txt') == 'file.txt'
        
        # 特殊字符处理
        assert sanitize_filename('file with spaces.doc') == 'file with spaces.doc'
    
    def test_generate_secure_token(self):
        """测试安全令牌生成"""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        # 令牌应该足够长
        assert len(token1) >= 32
        
        # 每次生成应该不同
        assert token1 != token2
    
    def test_escape_html(self):
        """测试HTML转义"""
        assert escape_html('<') == '&lt;'
        assert escape_html('>') == '&gt;'
        assert escape_html('&') == '&amp;'
        assert escape_html('"') == '&quot;'
        assert escape_html("'") == '&#x27;'
        assert escape_html('/') == '&#x2F;'
    
    def test_validate_file_extension(self):
        """测试文件扩展名验证"""
        allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        
        # 正确扩展名
        assert validate_file_extension('image.png', allowed) == True
        assert validate_file_extension('photo.JPG', allowed) == True
        assert validate_file_extension('animation.gif', allowed) == True
        
        # 错误扩展名
        assert validate_file_extension('file.exe', allowed) == False
        assert validate_file_extension('script.php', allowed) == False
        assert validate_file_extension('', allowed) == False


class TestPasswordHashing:
    """密码哈希测试类"""
    
    def test_password_hash_generation(self):
        """测试密码哈希生成"""
        password = 'mysecretpassword'
        hashed = generate_password_hash(password)
        
        # 哈希应该不同于原始密码
        assert hashed != password
        
        # 每次哈希应该不同（因为有随机salt）
        hashed2 = generate_password_hash(password)
        assert hashed != hashed2
    
    def test_password_verification(self):
        """测试密码验证"""
        password = 'mysecretpassword'
        hashed = generate_password_hash(password)
        
        # 正确密码应该验证通过
        assert check_password_hash(hashed, password) == True
        
        # 错误密码应该验证失败
        assert check_password_hash(hashed, 'wrongpassword') == False
    
    def test_different_hash_verification(self):
        """测试不同哈希值验证"""
        password = 'mysecretpassword'
        hashed1 = generate_password_hash(password)
        hashed2 = generate_password_hash(password)
        
        # 密码应该对任意哈希值都验证通过
        assert check_password_hash(hashed1, password) == True
        assert check_password_hash(hashed2, password) == True


class TestContentSecurityPolicy:
    """内容安全策略测试类"""
    
    def test_csp_header_format(self):
        """测试CSP头格式"""
        from security import ContentSecurityPolicy
        
        headers = ContentSecurityPolicy.get_header()
        csp = headers.get('Content-Security-Policy')
        
        # 应该包含关键指令
        assert "default-src 'self'" in csp
        assert "script-src" in csp
        assert "style-src" in csp
        assert "img-src" in csp
    
    def test_nonce_generation(self):
        """测试nonce值生成"""
        from security import ContentSecurityPolicy
        
        nonce1 = ContentSecurityPolicy.get_nonce()
        nonce2 = ContentSecurityPolicy.get_nonce()
        
        # 每次应该不同
        assert nonce1 != nonce2
        
        # 应该是有效的base64
        import base64
        decoded = base64.b64decode(nonce1)
        assert len(decoded) == 16


# 运行测试的命令
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
