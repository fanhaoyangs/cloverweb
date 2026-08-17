#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工时统计模块数据库初始化脚本
运行此脚本初始化工时统计相关的数据库表

使用方法:
    python init_workhour_db.py
"""
import os
import sys

# 添加父目录到路径，确保可以导入app模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Employee, WorkHourRecord, WorkHourItem, WorkHourConfig


def init_workhour_db():
    """初始化工时统计数据库"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表创建成功!")

        # 初始化默认配置
        default_configs = [
            ('project_table_id', '', '项目信息汇总表ID'),
            ('workhour_table_id', '', '工时统计表ID'),
            ('bot_open_id', '', '机器人Open ID'),
            ('notification_day', '28', '每月通知日期')
        ]

        for key, value, desc in default_configs:
            existing = WorkHourConfig.query.filter_by(config_key=key).first()
            if not existing:
                config = WorkHourConfig(
                    config_key=key,
                    config_value=value,
                    description=desc
                )
                db.session.add(config)
                print(f"添加配置: {key}")

        db.session.commit()
        print("默认配置初始化完成!")

        # 创建示例员工（仅用于测试）
        if Employee.query.count() == 0:
            sample_employees = [
                {
                    'feishu_user_id': 'test_user_001',
                    'name': '张三',
                    'email': 'zhangsan@example.com',
                    'department': '项目部'
                },
                {
                    'feishu_user_id': 'test_user_002',
                    'name': '李四',
                    'email': 'lisi@example.com',
                    'department': '项目部'
                },
                {
                    'feishu_user_id': 'test_user_003',
                    'name': '王五',
                    'email': 'wangwu@example.com',
                    'department': '设计部'
                }
            ]

            for emp_data in sample_employees:
                employee = Employee(**emp_data)
                db.session.add(employee)
                print(f"添加示例员工: {emp_data['name']}")

            db.session.commit()
            print("示例员工创建完成!")
            print("\n提示: 请在飞书配置页面更新员工的真实飞书用户ID")

        print("\n工时统计模块数据库初始化完成!")
        print("\n访问路径:")
        print("  - 工时填报: http://localhost:5000/workhour/")
        print("  - 管理后台: http://localhost:5000/workhour/admin/")
        print("  - 飞书配置: http://localhost:5000/workhour/admin/config/")


if __name__ == '__main__':
    print("=" * 50)
    print("工时统计模块数据库初始化")
    print("=" * 50)
    init_workhour_db()
