#!/usr/bin/env python
"""测试飞书通讯录同步"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 初始化 Flask 应用上下文
from app import app
with app.app_context():
    from feishu_api import FeishuAPI
    import json
    
    print("=" * 50)
    print("测试飞书通讯录同步")
    print("=" * 50)
    
    api = FeishuAPI()
    
    # 测试获取部门列表
    print("\n1. 测试获取部门列表...")
    import requests
    from feishu_config import FeishuWorkhourConfig
    from feishu_auth import feishu_workhour_auth
    
    token = feishu_workhour_auth.get_tenant_access_token()
    print(f"   Access Token: {'获取成功' if token else '获取失败'}")
    
    if token:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # 获取部门列表
        url = f"{FeishuWorkhourConfig.API_BASE_URL}/open-apis/contact/v3/departments"
        params = {'department_id_type': 'department_id', 'user_id_type': 'open_id', 'parent_department_id': '0'}
        
        resp = requests.get(url, headers=headers, params=params)
        result = resp.json()
        
        print(f"\n   部门列表响应:")
        print(f"   - code: {result.get('code')}")
        print(f"   - msg: {result.get('msg')}")
        
        if result.get('code') == 0:
            departments = result.get('data', {}).get('items', [])
            print(f"   - 部门数量: {len(departments)}")
            for dept in departments[:5]:  # 只显示前5个
                print(f"     - {dept.get('department_id')}: {dept.get('name', 'N/A')}")
        else:
            print(f"   - 错误详情: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 获取用户列表
        print("\n2. 测试获取用户列表...")
        users = api.get_contact_users()
        print(f"   获取到 {len(users)} 个用户")
        
        if users:
            print("\n   用户列表（前5个）:")
            for i, user in enumerate(users[:5]):
                print(f"   - 姓名: '{user.get('name')}' | ID: {user.get('user_id')}")
            
            # 获取原始用户数据查看字段
            print("\n3. 查看原始用户数据结构...")
            url2 = f"{FeishuWorkhourConfig.API_BASE_URL}/open-apis/contact/v3/users"
            params2 = {
                'department_id_type': 'department_id',
                'user_id_type': 'open_id',
                'department_id': '0',  # 根部门
                'page_size': 1
            }
            resp2 = requests.get(url2, headers=headers, params=params2)
            result2 = resp2.json()
            
            if result2.get('code') == 0:
                items = result2.get('data', {}).get('items', [])
                if items:
                    print("\n   第一个用户的所有字段:")
                    for key, value in items[0].items():
                        print(f"   - {key}: {value}")
        else:
            print("   未获取到任何用户")
    else:
        print("   无法获取 Access Token，请检查飞书应用配置")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
