"""
飞书配置模块
管理飞书开放平台的应用配置信息

支持两个飞书应用：
1. 主应用（FEISHU_APP_ID/SECRET）- 用于导出文档等
2. 工时应用（FEISHU_WORKHOUR_*）- 用于工时提交和通讯录同步
"""
import os
import urllib.parse


class FeishuConfig:
    """飞书主应用配置（用于导出文档等）"""
    APP_ID = os.environ.get('FEISHU_APP_ID', '')
    APP_SECRET = os.environ.get('FEISHU_APP_SECRET', '')
    REDIRECT_URI = os.environ.get('FEISHU_REDIRECT_URI', 'http://localhost:5000/admin/feishu/callback')
    
    APP_TOKEN = os.environ.get('FEISHU_APP_TOKEN', '')
    
    SCOPES = os.environ.get('FEISHU_SCOPES', 'docs:document.content:read docs:document.media:download docx:document:readonly sheets:spreadsheet:read auth:user_access_token:read')
    
    API_BASE_URL = 'https://open.feishu.cn'
    
    TOKEN_EXPIRE_SECONDS = 7200
    
    @classmethod
    def is_configured(cls):
        """检查是否已配置飞书应用"""
        return bool(cls.APP_ID and cls.APP_SECRET)
    
    @classmethod
    def get_auth_url(cls, state=''):
        """获取飞书OAuth授权URL"""
        base_url = f"{cls.API_BASE_URL}/open-apis/authen/v1/authorize"
        params = {
            'app_id': cls.APP_ID,
            'redirect_uri': cls.REDIRECT_URI,
            'state': state,
            'scope': cls.SCOPES
        }
        query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        return f"{base_url}?{query_string}"


class FeishuWorkhourConfig:
    """飞书工时应用配置（用于工时提交和通讯录同步）"""
    APP_ID = os.environ.get('FEISHU_WORKHOUR_APP_ID', '')
    APP_SECRET = os.environ.get('FEISHU_WORKHOUR_APP_SECRET', '')
    
    # 多维表格配置 - 一个App Token，包含多个数据表
    BITABLE_APP_TOKEN = os.environ.get('FEISHU_WORKHOUR_BITABLE_APP_TOKEN', '')
    PROJECT_TABLE_ID = os.environ.get('FEISHU_WORKHOUR_PROJECT_TABLE_ID', '')   # 项目列表表ID
    WORKHOUR_TABLE_ID = os.environ.get('FEISHU_WORKHOUR_WORKHOUR_TABLE_ID', '') # 工时统计表ID
    
    # Bot配置
    BOT_OPEN_ID = os.environ.get('FEISHU_WORKHOUR_BOT_OPEN_ID', '')
    
    API_BASE_URL = 'https://open.feishu.cn'
    
    # OAuth 配置
    SCOPES = 'contact:user.base:readonly'
    
    TOKEN_EXPIRE_SECONDS = 7200
    
    @classmethod
    def is_configured(cls):
        """检查是否已配置飞书工时应用（仅检查 App ID 和 Secret，其他配置从数据库读取）"""
        return bool(cls.APP_ID and cls.APP_SECRET)
    
    @classmethod
    def get_auth_url(cls, redirect_uri, state=''):
        """获取飞书OAuth授权URL"""
        base_url = f"{cls.API_BASE_URL}/open-apis/authen/v1/authorize"
        params = {
            'app_id': cls.APP_ID,
            'redirect_uri': redirect_uri,
            'state': state,
            'scope': cls.SCOPES
        }
        query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    @classmethod
    def get_bitable_url(cls):
        """获取多维表格的基础URL"""
        return f"{cls.API_BASE_URL}/open-apis/bitable/v1/apps/{cls.BITABLE_APP_TOKEN}"
