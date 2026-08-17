#!/usr/bin/env python
"""
数据库迁移脚本：为 employees 表添加 user_id 字段
运行方式：python migrate_add_employee_user_id.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'posts.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(employees)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in columns:
            cursor.execute('''
                ALTER TABLE employees 
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            ''')
            print("✓ 添加 user_id 字段成功")
        else:
            print("✓ user_id 字段已存在")
        
        conn.commit()
        print("\n迁移完成！")
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
    else:
        migrate()
