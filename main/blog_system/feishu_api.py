"""
飞书文档API模块
封装飞书文档相关的API调用

支持两个飞书应用:
1. FeishuDocAPI - 主应用(导出文档等)，使用 FeishuConfig
2. FeishuAPI - 工时应用(工时提交、通讯录同步)，使用 FeishuWorkhourConfig
"""
import requests
import json
import logging
from feishu_config import FeishuConfig, FeishuWorkhourConfig
from feishu_auth import feishu_auth, feishu_workhour_auth

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('logs/feishu_import.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


class FeishuDocAPI:
    """飞书文档API"""
    
    def __init__(self):
        self.config = FeishuConfig()
    
    def _get_headers(self, token_type='tenant', user_token=None):
        """获取请求头"""
        if token_type == 'user' and user_token:
            token = user_token
        else:
            token = feishu_auth.get_tenant_access_token()
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_doc_list(self, user_token=None, folder_token=None, page_size=50, page_token=None):
        """获取文档列表"""
        url = f"{self.config.API_BASE_URL}/open-apis/drive/v1/files"
        
        headers = self._get_headers('user' if user_token else 'tenant', user_token)
        params = {
            'page_size': page_size
        }
        
        if folder_token:
            params['folder_token'] = folder_token
        if page_token:
            params['page_token'] = page_token
        
        response = requests.get(url, headers=headers, params=params)
        result = response.json()
        
        if result.get('code') == 0:
            return result.get('data', {})
        else:
            raise Exception(f"获取文档列表失败: {result.get('msg')}, code: {result.get('code')}")
    
    def get_root_folder_token(self):
        """获取我的空间根目录token"""
        url = f"{self.config.API_BASE_URL}/open-apis/drive/v1/root_folder/meta"
        
        headers = self._get_headers('tenant')
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get('code') == 0:
            return result.get('data', {}).get('token')
        else:
            return None
    
    def search_docs(self, query='', page_size=50, page_token=None):
        """搜索文档"""
        url = f"{self.config.API_BASE_URL}/open-apis/drive/v1/files/search"
        
        headers = self._get_headers('tenant')
        params = {
            'page_size': page_size
        }
        
        if query:
            params['query'] = query
        if page_token:
            params['page_token'] = page_token
        
        response = requests.post(url, headers=headers, json=params)
        result = response.json()
        
        if result.get('code') == 0:
            return result.get('data', {})
        else:
            raise Exception(f"搜索文档失败: {result.get('msg')}")
    
    def get_doc_content(self, doc_token, doc_type='docx', user_token=None):
        """获取文档内容"""
        if doc_type == 'docx':
            return self._get_docx_content(doc_token, user_token)
        elif doc_type == 'wiki':
            return self._get_wiki_content(doc_token, user_token)
        else:
            return self._get_docx_content(doc_token, user_token)
    
    def _get_docx_content(self, doc_token, user_token=None):
        """获取DocX文档内容"""
        url = f"{self.config.API_BASE_URL}/open-apis/docx/v1/documents/{doc_token}/blocks"
        
        headers = self._get_headers('user' if user_token else 'tenant', user_token)
        params = {
            'page_size': 500
        }
        
        logger.info(f"Fetching docx content: {url}")
        logger.debug(f"Using user_token: {'Yes' if user_token else 'No'}")
        
        all_blocks = []
        page_token = None
        
        while True:
            if page_token:
                params['page_token'] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            logger.debug(f"API Response code: {result.get('code')}, msg: {result.get('msg')}")
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                all_blocks.extend(items)
                logger.info(f"Got {len(items)} blocks, total: {len(all_blocks)}")
                
                page_token = data.get('page_token')
                if not page_token or not data.get('has_more'):
                    break
            else:
                logger.error(f"API Error: {result}")
                raise Exception(f"获取文档内容失败: {result.get('msg')}, code: {result.get('code')}, response: {result}")
        
        logger.info(f"Total blocks fetched: {len(all_blocks)}")
        return {
            'document_id': doc_token,
            'blocks': all_blocks
        }
    
    def get_block_info(self, document_id, block_id, user_token=None):
        """获取单个块的详细信息"""
        url = f"{self.config.API_BASE_URL}/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}"
        
        headers = self._get_headers('user' if user_token else 'tenant', user_token)
        
        logger.debug(f"Fetching block info: {url}")
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        logger.debug(f"Block info response: code={result.get('code')}, data keys={list(result.get('data', {}).keys())}")
        
        if result.get('code') == 0:
            data = result.get('data', {})
            logger.debug(f"Block info data: {data}")
            return data
        else:
            logger.warning(f"获取块信息失败：{result.get('msg')}, code: {result.get('code')}")
            return None
    
    def _get_wiki_content(self, wiki_token, user_token=None):
        """获取知识库文档内容"""
        url = f"{self.config.API_BASE_URL}/open-apis/wiki/v2/spaces/{wiki_token}/nodes"
        
        headers = self._get_headers('user' if user_token else 'tenant', user_token)
        params = {
            'page_size': 50
        }
        
        all_nodes = []
        page_token = None
        
        while True:
            if page_token:
                params['page_token'] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                all_nodes.extend(items)
                
                page_token = data.get('page_token')
                if not page_token or not data.get('has_more'):
                    break
            else:
                raise Exception(f"获取知识库内容失败: {result.get('msg')}")
        
        return {
            'wiki_token': wiki_token,
            'nodes': all_nodes
        }
    
    def get_doc_meta(self, doc_token, user_token=None):
        """获取文档元数据"""
        url = f"{self.config.API_BASE_URL}/open-apis/docx/v1/documents/{doc_token}"
        
        headers = self._get_headers('user' if user_token else 'tenant', user_token)
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get('code') == 0:
            data = result.get('data', {})
            document = data.get('document', {})
            return {
                'title': document.get('title', ''),
                'document_id': document.get('document_id', ''),
                'revision_id': document.get('revision_id', 0)
            }
        else:
            raise Exception(f"获取文档元数据失败: {result.get('msg')}, code: {result.get('code')}")
    
    def get_block_children(self, doc_token, block_id):
        """获取块的子块"""
        url = f"{self.config.API_BASE_URL}/open-apis/docx/v1/documents/{doc_token}/blocks/{block_id}/children"
        
        headers = self._get_headers('tenant')
        params = {
            'page_size': 500
        }
        
        all_children = []
        page_token = None
        
        while True:
            if page_token:
                params['page_token'] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                all_children.extend(items)
                
                page_token = data.get('page_token')
                if not page_token or not data.get('has_more'):
                    break
            else:
                raise Exception(f"获取块子元素失败: {result.get('msg')}")
        
        return all_children
    
    def download_image(self, file_token, save_path=None):
        """下载图片"""
        url = f"{self.config.API_BASE_URL}/open-apis/drive/v1/medias/{file_token}/download"
        
        headers = self._get_headers('tenant')
        
        response = requests.get(url, headers=headers, stream=True)
        
        if response.status_code == 200:
            if save_path:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return save_path
            else:
                return response.content
        else:
            raise Exception(f"下载图片失败: {response.status_code}")
    
    def get_sheet_content(self, sheet_token, user_token=None):
        """获取电子表格内容"""
        # 第一步：获取工作表列表（包含列宽信息）
        url = f"{self.config.API_BASE_URL}/open-apis/sheets/v3/spreadsheets/{sheet_token}/sheets/query"
        
        headers = self._get_headers('user' if user_token else 'tenant', user_token)
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        logger.debug(f"Sheet list response: code={result.get('code')}, msg={result.get('msg')}")
        
        if result.get('code') == 0:
            data = result.get('data', {})
            sheets = data.get('sheets', [])
            
            logger.debug(f"Sheet API response data keys: {list(data.keys())}")
            logger.debug(f"Found {len(sheets) if sheets else 0} sheets in spreadsheet")
            
            all_sheets_data = []
            for sheet in sheets:
                sheet_id = sheet.get('sheet_id')
                sheet_title = sheet.get('title', '')
                
                logger.debug(f"Processing sheet: {sheet_title}, id: {sheet_id}")
                
                # 获取合并单元格信息
                merges = self._get_sheet_merge_info(sheet_token, sheet_id, user_token)
                
                # 获取工作表数据
                sheet_data = self._get_sheet_data(sheet_token, sheet_id, user_token)
                logger.debug(f"Sheet {sheet_title} data rows: {len(sheet_data) if sheet_data else 0}")
                
                all_sheets_data.append({
                    'title': sheet_title,
                    'data': sheet_data,
                    'column_width': [],  # API 不返回可靠的列宽信息，由用户手动设置
                    'merges': merges
                })
            
            return all_sheets_data
        else:
            raise Exception(f"获取电子表格失败：{result.get('msg')}, code: {result.get('code')}")
    
    def _get_sheet_merge_info(self, spreadsheet_token, sheet_id, user_token=None):
        """获取工作表的合并单元格信息"""
        url = f"{self.config.API_BASE_URL}/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/{sheet_id}"
        
        headers = self._get_headers('user' if user_token else 'tenant', user_token)
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get('code') == 0:
            sheet_data = result.get('data', {}).get('sheet', {})
            merges = sheet_data.get('merges', [])
            logger.debug(f"Sheet {sheet_id} merges: {len(merges) if merges else 0} merged regions")
            return merges
        else:
            logger.debug(f"获取合并信息失败：{result.get('msg')}")
            return []
    
    def _get_sheet_data(self, spreadsheet_token, sheet_id, user_token=None):
        """获取单个工作表数据"""
        # 使用 v2 API 读取数据，range 在 URL 路径中
        url = f"{self.config.API_BASE_URL}/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}"
        
        headers = self._get_headers('user' if user_token else 'tenant', user_token)
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        logger.debug(f"Sheet data response for {sheet_id}: code={result.get('code')}, msg={result.get('msg')}")
        
        if result.get('code') == 0:
            values = result.get('data', {}).get('valueRange', {}).get('values', [])
            logger.debug(f"Got {len(values) if values else 0} rows from sheet {sheet_id}")
            return values
        else:
            logger.warning(f"获取工作表数据失败：{result.get('msg')}, code: {result.get('code')}")
            return []


feishu_doc_api = FeishuDocAPI()


# ==================== 工时统计相关API ====================

def _get_db_config(key, default=None):
    """从数据库获取配置值"""
    try:
        from models import WorkHourConfig
        config = WorkHourConfig.query.filter_by(config_key=key).first()
        return config.config_value if config else default
    except Exception:
        return default


class FeishuAPI:
    """飞书工时统计API - 使用工时应用配置"""
    
    def __init__(self):
        self.config = FeishuWorkhourConfig()
        # 从数据库读取配置（优先于环境变量）
        self._bitable_app_token = _get_db_config('bitable_app_token') or self.config.BITABLE_APP_TOKEN
        self._project_table_id = _get_db_config('project_table_id') or self.config.PROJECT_TABLE_ID
        self._workhour_table_id = _get_db_config('workhour_table_id') or self.config.WORKHOUR_TABLE_ID
        self._bot_open_id = _get_db_config('bot_open_id') or self.config.BOT_OPEN_ID
    
    def _get_headers(self, token_type='tenant'):
        """获取请求头"""
        token = feishu_workhour_auth.get_tenant_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_project_list(self):
        """从飞书多维表格获取项目列表，按项目名称倒序排列"""
        logger.info(f"开始获取项目列表, bitable_app_token: {self._bitable_app_token}, project_table_id: {self._project_table_id}")
        
        if not self._bitable_app_token or not self._project_table_id:
            logger.warning('多维表格App Token或项目表ID未配置')
            return []
        
        try:
            # 获取所有记录
            all_records = self._get_all_table_records(self._project_table_id)
            logger.info(f"从飞书获取到 {len(all_records)} 条原始记录")
            
            # 提取项目名称
            projects = []
            for i, record in enumerate(all_records):
                fields = record.get('fields', {})
                project_name = None
                
                for field_name, field_value in fields.items():
                    if isinstance(field_value, str) and field_value.strip():
                        project_name = field_value.strip()
                        break
                    elif isinstance(field_value, list) and len(field_value) > 0:
                        first_item = field_value[0]
                        if isinstance(first_item, str):
                            project_name = first_item.strip()
                        elif isinstance(first_item, dict) and 'text' in first_item:
                            project_name = first_item['text'].strip()
                        if project_name:
                            break
                
                if project_name:
                    projects.append(project_name)
                else:
                    logger.warning(f"记录{i}未能提取到项目名称, fields: {fields}")
            
            # 按项目名称倒序排列
            projects.sort(reverse=True)
            logger.info(f"最终提取的项目列表（倒序）: {projects}")
            return projects
                
        except Exception as e:
            logger.error(f"获取项目列表异常: {e}", exc_info=True)
            return []
    
    def _get_all_table_records(self, table_id, filter_formula=None):
        """获取多维表格所有原始记录（返回原始记录列表，不提取项目名称）"""
        if not self._bitable_app_token:
            logger.warning('多维表格App Token未配置')
            return []
            
        try:
            url = f"{self.config.API_BASE_URL}/open-apis/bitable/v1/apps/{self._bitable_app_token}/tables/{table_id}/records"
            
            all_records = []
            page_token = None
            
            while True:
                params = {'page_size': 100}
                if filter_formula:
                    params['filter_formula'] = filter_formula
                if page_token:
                    params['page_token'] = page_token
                
                logger.info(f"请求飞书多维表格: {url}, page_token: {page_token}")
                
                response = requests.get(url, headers=self._get_headers(), params=params)
                result = response.json()
                
                logger.info(f"飞书API响应code: {result.get('code')}, msg: {result.get('msg')}")
                
                if result.get('code') == 0:
                    records = result.get('data', {}).get('items', [])
                    all_records.extend(records)
                    logger.info(f"本页获取到 {len(records)} 条记录, 累计: {len(all_records)}")
                    
                    # 检查是否还有更多分页
                    has_more = result.get('data', {}).get('has_more', False)
                    page_token = result.get('data', {}).get('page_token')
                    
                    if not has_more or not page_token:
                        break
                else:
                    logger.warning(f"获取记录失败: {result.get('msg')}, code: {result.get('code')}")
                    break
            
            logger.info(f"共获取到 {len(all_records)} 条原始记录")
            return all_records
                
        except Exception as e:
            logger.error(f"获取记录异常: {e}", exc_info=True)
            return []
    
    def _get_table_records(self, table_id, filter_formula=None, sort_field=None, sort_order='desc'):
        """获取多维表格记录（已废弃，请使用 _get_all_table_records + 手动提取）"""
        records = self._get_all_table_records(table_id, filter_formula)
        
        # 提取项目名称
        projects = []
        for i, record in enumerate(records):
            fields = record.get('fields', {})
            project_name = None
            
            for field_name, field_value in fields.items():
                if isinstance(field_value, str) and field_value.strip():
                    project_name = field_value.strip()
                    break
                elif isinstance(field_value, list) and len(field_value) > 0:
                    first_item = field_value[0]
                    if isinstance(first_item, str):
                        project_name = first_item.strip()
                    elif isinstance(first_item, dict) and 'text' in first_item:
                        project_name = first_item['text'].strip()
                    if project_name:
                        break
            
            if project_name:
                projects.append(project_name)
            else:
                logger.warning(f"记录{i}未能提取到项目名称, fields: {fields}")
        
        logger.info(f"最终提取的项目列表: {projects}")
        return projects
    
    def send_workhour_reminder(self, user_id, user_name, month, work_days, form_url):
        """
        发送工时填报提醒消息
        
        Args:
            user_id: 飞书用户ID
            user_name: 用户姓名
            month: 月份
            work_days: 应填工作日天数
            form_url: 填报页面URL
        """
        if not self._bot_open_id:
            logger.warning('机器人Open ID未配置')
            return False
        
        try:
            url = f"{self.config.API_BASE_URL}/open-apis/im/v1/messages"
            
            # 构造卡片消息
            card_content = {
                "msg_type": "interactive",
                "content": {
                    "card": {
                        "header": {
                            "title": {
                                "tag": "plain_text",
                                "content": f"📋 {month}月项目工时填报提醒"
                            },
                            "template": "green"
                        },
                        "elements": [
                            {
                                "tag": "markdown",
                                "content": f"**您好，{user_name}！**\n\n{month}月的项目工时统计填报已开始，请及时完成。"
                            },
                            {
                                "tag": "hr"
                            },
                            {
                                "tag": "div",
                                "fields": [
                                    {
                                        "is_short": True,
                                        "text": {
                                            "tag": "lark_md",
                                            "content": f"**📅 填报期限**\n本月末前"
                                        }
                                    },
                                    {
                                        "is_short": True,
                                        "text": {
                                            "tag": "lark_md",
                                            "content": f"**📊 应填工作日**\n{work_days} 天"
                                        }
                                    }
                                ]
                            },
                            {
                                "tag": "action",
                                "actions": [
                                    {
                                        "tag": "button",
                                        "text": {
                                            "tag": "plain_text",
                                            "content": "立即填报"
                                        },
                                        "type": "primary",
                                        "url": form_url
                                    }
                                ]
                            },
                            {
                                "tag": "note",
                                "elements": [
                                    {
                                        "tag": "plain_text",
                                        "content": "如有疑问，请联系管理员。"
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
            
            payload = {
                'receive_id': user_id,
                'msg_type': 'interactive',
                'content': json.dumps(card_content['content'], ensure_ascii=False)
            }
            
            # 使用机器人的 open_id 发送
            response = requests.post(
                f"{url}?receive_id_type=open_id",
                headers=self._get_headers(),
                json=payload
            )
            result = response.json()
            
            if result.get('code') == 0:
                logger.info(f"发送提醒成功: {user_name}")
                return True
            else:
                logger.warning(f"发送提醒失败: {result.get('msg')}")
                return False
                
        except Exception as e:
            logger.error(f"发送提醒异常: {e}")
            return False

    def get_contact_users(self):
        """
        从飞书通讯录获取用户列表

        Returns:
            List of dict: [{'user_id': xxx, 'name': xxx, 'email': xxx, 'department': xxx}, ...]
        """
        try:
            # 先获取所有部门信息（用于将部门ID转换为名称）
            department_names = self._get_all_department_names()

            # 获取根部门下的所有用户
            all_users = self._get_users_recursive('0', department_names)

            # 去重
            seen = set()
            unique_users = []
            for user in all_users:
                if user.get('user_id') not in seen:
                    seen.add(user.get('user_id'))
                    unique_users.append(user)

            logger.info(f"从通讯录获取到 {len(unique_users)} 个用户")
            return unique_users

        except Exception as e:
            logger.error(f"获取通讯录用户异常: {e}")
            return []

    def _get_all_department_names(self):
        """获取所有部门的名称映射"""
        department_names = {}
        try:
            def fetch_sub_departments(parent_id):
                url = f"{self.config.API_BASE_URL}/open-apis/contact/v3/departments"
                params = {
                    'department_id_type': 'department_id',
                    'user_id_type': 'open_id',
                    'parent_department_id': parent_id
                }
                response = requests.get(url, headers=self._get_headers(), params=params)
                result = response.json()

                if result.get('code') == 0:
                    items = result.get('data', {}).get('items', [])
                    for dept in items:
                        dept_id = dept.get('department_id')
                        dept_name = dept.get('name', '')
                        if dept_id:
                            department_names[dept_id] = dept_name
                            # 递归获取子部门
                            fetch_sub_departments(dept_id)

            fetch_sub_departments('0')
        except Exception as e:
            logger.warning(f"获取部门名称失败: {e}")

        logger.info(f"获取到 {len(department_names)} 个部门: {department_names}")
        return department_names

    def _get_users_recursive(self, department_id, department_names):
        """递归获取部门及其子部门的用户"""
        all_users = []
        try:
            # 获取当前部门的用户
            users = self._get_users_by_department(department_id, department_names)
            all_users.extend(users)

            # 获取子部门
            url = f"{self.config.API_BASE_URL}/open-apis/contact/v3/departments"
            params = {
                'department_id_type': 'department_id',
                'user_id_type': 'open_id',
                'parent_department_id': department_id
            }
            response = requests.get(url, headers=self._get_headers(), params=params)
            result = response.json()

            if result.get('code') == 0:
                sub_departments = result.get('data', {}).get('items', [])
                for dept in sub_departments:
                    sub_dept_id = dept.get('department_id')
                    if sub_dept_id:
                        sub_users = self._get_users_recursive(sub_dept_id, department_names)
                        all_users.extend(sub_users)

        except Exception as e:
            logger.warning(f"递归获取用户失败 (部门 {department_id}): {e}")

        return all_users

    def _get_users_by_department(self, department_id, department_names):
        """获取指定部门的用户列表"""
        try:
            url = f"{self.config.API_BASE_URL}/open-apis/contact/v3/users"
            params = {
                'department_id_type': 'department_id',
                'user_id_type': 'open_id',
                'department_id': department_id,
                'page_size': 50
            }

            response = requests.get(url, headers=self._get_headers(), params=params)
            result = response.json()

            users = []
            if result.get('code') == 0:
                items = result.get('data', {}).get('items', [])
                for user in items:
                    open_id = user.get('open_id')

                    name = user.get('name') or user.get('nickname') or user.get('en_name', '')

                    if not name and open_id:
                        user_detail = self._get_user_detail(open_id)
                        if user_detail:
                            name = user_detail.get('name', '')

                    if not name and open_id:
                        name = f"用户_{open_id[-8:]}"

                    # 获取部门名称
                    department = ''
                    dept_ids = user.get('department_ids', [])
                    if dept_ids:
                        department = department_names.get(dept_ids[0], '')

                    users.append({
                        'user_id': open_id,
                        'name': name,
                        'email': user.get('email', ''),
                        'department': department
                    })
            else:
                logger.warning(f"获取部门用户失败: code={result.get('code')}, msg={result.get('msg')}")
            return users

        except Exception as e:
            logger.error(f"获取部门用户异常: {e}")
            return []

    def _get_user_detail(self, open_id):
        """获取单个用户的详细信息"""
        try:
            url = f"{self.config.API_BASE_URL}/open-apis/contact/v3/users/{open_id}"
            params = {
                'user_id_type': 'open_id',
                'department_id_type': 'department_id'
            }

            response = requests.get(url, headers=self._get_headers(), params=params)
            result = response.json()

            if result.get('code') == 0:
                user = result.get('data', {}).get('user', {})
                return {
                    'name': user.get('name', ''),
                    'email': user.get('email', ''),
                    'mobile': user.get('mobile', ''),
                    'department': user.get('department_id', '')
                }
            return None
        except Exception as e:
            logger.debug(f"获取用户详情失败: {e}")
            return None
