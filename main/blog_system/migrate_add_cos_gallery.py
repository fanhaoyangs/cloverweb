"""
数据库迁移脚本：添加 COS 图片库相关表
运行方式：python migrate_add_cos_gallery.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'posts.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cos_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                color VARCHAR(7) DEFAULT '#666666',
                sort_order INTEGER DEFAULT 0
            )
        ''')
        print("✓ 创建 cos_tags 表成功")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cos_image_tags (
                image_key VARCHAR(500) NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (image_key, tag_id),
                FOREIGN KEY (tag_id) REFERENCES cos_tags(id) ON DELETE CASCADE
            )
        ''')
        print("✓ 创建 cos_image_tags 表成功")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cos_image_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_key VARCHAR(500) NOT NULL,
                post_id INTEGER,
                used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE SET NULL
            )
        ''')
        print("✓ 创建 cos_image_usage 表成功")
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cos_image_usage_image_key 
            ON cos_image_usage(image_key)
        ''')
        print("✓ 创建索引成功")
        
        conn.commit()
        print("\n迁移完成！COS 图片库表已创建。")
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        print("请先运行 init_db.py 初始化数据库")
    else:
        migrate()
