#!/usr/bin/env python3
"""
数据库迁移脚本：添加 tags 和 post_tags 表
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'posts.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    slug = db.Column(db.String(40), unique=True, nullable=False)


def migrate():
    """执行迁移"""
    with app.app_context():
        # 检查表是否已存在
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        print(f"现有表: {existing_tables}")
        
        if 'tags' not in existing_tables:
            print("创建 tags 表...")
            Tag.__table__.create(db.engine)
            print("✓ tags 表创建完成")
        else:
            print("tags 表已存在，跳过")
        
        if 'post_tags' not in existing_tables:
            print("创建 post_tags 表...")
            # 使用原生 SQL 创建表，避免外键依赖问题
            with db.engine.connect() as conn:
                conn.execute(db.text('''
                    CREATE TABLE post_tags (
                        post_id INTEGER NOT NULL,
                        tag_id INTEGER NOT NULL,
                        PRIMARY KEY (post_id, tag_id),
                        FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                    )
                '''))
                conn.commit()
            print("✓ post_tags 表创建完成")
        else:
            print("post_tags 表已存在，跳过")
        
        print("\n迁移完成！")


if __name__ == '__main__':
    migrate()
