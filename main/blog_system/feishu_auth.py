"""
飞书认证模块
处理飞书OAuth授权流程和令牌管理

支持两个飞书应用的独立认证：
1. 主应用 - 用于导出文档等
2. 工时应用 - 用于工时提交和通讯录同步
"""
import json
import time
import requests
from feishu_config import FeishuConfig, FeishuWorkhourConfig


class FeishuAuth:
    """飞书主应用认证管理（用于导出文档等）"""
    
    def __init__(self):
        self.config = FeishuConfig()
        self._tenant_access_token = None
        self._tenant_token_expire = 0
        self._user_access_token = None
        self._user_token_expire = 0
    
    def get_tenant_access_token(self):
        """获取tenant_access_token（应用访问令牌）"""
        if self._tenant_access_token and time.time() < self._tenant_token_expire:
            return self._tenant_access_token
        
        url = f"{self.config.API_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal"
        data = {
            'app_id': self.config.APP_ID,
            'app_secret': self.config.APP_SECRET
        }
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('code') == 0:
            self._tenant_access_token = result.get('tenant_access_token')
            expire = result.get('expire', 7200)
            self._tenant_token_expire = time.time() + expire - 300
            return self._tenant_access_token
        else:
            raise Exception(f"获取tenant_access_token失败: {result.get('msg')}")
    
    def get_user_access_token(self, code):
        """通过授权码获取user_access_token"""
        url = f"{self.config.API_BASE_URL}/open-apis/authen/v1/oidc/access_token"
        
        tenant_token = self.get_tenant_access_token()
        headers = {
            'Authorization': f'Bearer {tenant_token}',
            'Content-Type': 'application/json'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get('code') == 0:
            data = result.get('data', {})
            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in'),
                'token_type': data.get('token_type'),
                'user_id': data.get('user_id'),
                'open_id': data.get('open_id')
            }
        else:
            raise Exception(f"获取user_access_token失败: {result.get('msg')}")
    
    def refresh_user_access_token(self, refresh_token):
        """刷新user_access_token"""
        url = f"{self.config.API_BASE_URL}/open-apis/authen/v1/oidc/refresh_access_token"
        
        tenant_token = self.get_tenant_access_token()
        headers = {
            'Authorization': f'Bearer {tenant_token}',
            'Content-Type': 'application/json'
        }
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get('code') == 0:
            data = result.get('data', {})
            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in')
            }
        else:
            raise Exception(f"刷新user_access_token失败: {result.get('msg')}")
    
    def get_user_info(self, user_access_token):
        """获取用户信息"""
        url = f"{self.config.API_BASE_URL}/open-apis/authen/v1/user_info"
        headers = {
            'Authorization': f'Bearer {user_access_token}'
        }
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get('code') == 0:
            return result.get('data', {})
        else:
            raise Exception(f"获取用户信息失败: {result.get('msg')}")


class FeishuWorkhourAuth:
    """飞书工时应用认证管理（用于工时提交和通讯录同步）"""
    
    def __init__(self):
        self.config = FeishuWorkhourConfig()
        self._tenant_access_token = None
        self._tenant_token_expire = 0
    
    def get_tenant_access_token(self):
        """获取tenant_access_token（应用访问令牌）"""
        if not self.config.is_configured():
            raise Exception("飞书工时应用未配置，请设置 FEISHU_WORKHOUR_APP_ID 和 FEISHU_WORKHOUR_APP_SECRET")
        
        if self._tenant_access_token and time.time() < self._tenant_token_expire:
            return self._tenant_access_token
        
        url = f"{self.config.API_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal"
        data = {
            'app_id': self.config.APP_ID,
            'app_secret': self.config.APP_SECRET
        }
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('code') == 0:
            self._tenant_access_token = result.get('tenant_access_token')
            expire = result.get('expire', 7200)
            self._tenant_token_expire = time.time() + expire - 300
            return self._tenant_access_token
        else:
            raise Exception(f"获取工时应用tenant_access_token失败: {result.get('msg')}")
    
    def get_user_access_token(self, code):
        """通过授权码获取user_access_token"""
        # 使用飞书标准的OAuth 2.0端点
        url = f"{self.config.API_BASE_URL}/open-apis/authen/v1/access_token"
        
        tenant_token = self.get_tenant_access_token()
        headers = {
            'Authorization': f'Bearer {tenant_token}',
            'Content-Type': 'application/json'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code
        }
        
        print(f"请求飞书API: {url}")
        print(f"请求数据: {data}")
        
        response = requests.post(url, headers=headers, json=data)
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        try:
            result = response.json()
            print(f"飞书API响应: {result}")  # 打印完整响应
        except Exception as e:
            print(f"解析响应失败: {e}")
            print(f"响应内容: {response.text}")
            raise Exception(f"解析飞书API响应失败: {e}")
        
        if result.get('code') == 0:
            data = result.get('data', {})
            print(f"飞书API返回的数据: {data}")  # 打印数据部分
            
            # 飞书标准OAuth 2.0端点返回的字段
            open_id = data.get('open_id')
            user_id = data.get('user_id')
            access_token = data.get('access_token')
            
            print(f"提取的open_id: {open_id}")
            print(f"提取的user_id: {user_id}")
            print(f"提取的access_token: {access_token[:20]}...")  # 只打印前20个字符
            
            # 检查必要字段
            if not access_token:
                raise Exception("飞书API未返回access_token")
            if not open_id:
                raise Exception("飞书API未返回open_id")
            
            return {
                'access_token': access_token,
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in'),
                'token_type': data.get('token_type'),
                'user_id': user_id,
                'open_id': open_id
            }
        else:
            raise Exception(f"获取user_access_token失败: {result.get('msg')}, code: {result.get('code')}")
    
    def get_user_info(self, user_access_token):
        """获取用户信息"""
        url = f"{self.config.API_BASE_URL}/open-apis/authen/v1/user_info"
        headers = {
            'Authorization': f'Bearer {user_access_token}'
        }
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get('code') == 0:
            return result.get('data', {})
        else:
            raise Exception(f"获取用户信息失败: {result.get('msg')}")
    
    def get_headers(self, token_type='tenant'):
        """获取请求头"""
        if token_type == 'tenant':
            token = self.get_tenant_access_token()
        else:
            token = None
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }


# 主应用认证实例
feishu_auth = FeishuAuth()

# 工时应用认证实例
feishu_workhour_auth = FeishuWorkhourAuth()
