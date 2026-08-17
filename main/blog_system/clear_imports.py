#!/usr/bin/env python3
"""
清理飞书导入历史记录
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'posts.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class FeishuImport(db.Model):
    __tablename__ = 'feishu_imports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    doc_token = db.Column(db.String(100), nullable=False)
    doc_title = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text)
    post_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)


def clear_imports():
    """清理所有导入历史"""
    with app.app_context():
        count = FeishuImport.query.count()
        print(f"当前导入历史记录数: {count}")
        
        if count == 0:
            print("没有需要清理的记录")
            return
        
        print(f"\n即将删除所有 {count} 条导入历史记录")
        confirm = input("确认删除？(y/n): ")
        
        if confirm.lower() == 'y':
            FeishuImport.query.delete()
            db.session.commit()
            print(f"✓ 已删除 {count} 条记录")
        else:
            print("已取消")


def list_imports():
    """列出所有导入历史"""
    with app.app_context():
        imports = FeishuImport.query.order_by(FeishuImport.created_at.desc()).all()
        
        if not imports:
            print("没有导入历史记录")
            return
        
        print(f"\n导入历史记录 (共 {len(imports)} 条):")
        print("-" * 80)
        for imp in imports:
            print(f"ID: {imp.id} | 状态: {imp.status} | 标题: {imp.doc_title or 'N/A'}")
            print(f"   创建时间: {imp.created_at}")
        print("-" * 80)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        list_imports()
    else:
        list_imports()
        print()
        clear_imports()
