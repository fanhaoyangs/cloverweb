#!/usr/bin/env python3
"""
数据库初始化脚本
独立运行，不依赖app.py
"""
import os
import sys

# 确保路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime


# 创建临时Flask应用
app = Flask(__name__)

# 使用绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'posts.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# 定义模型
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(70), unique=True, nullable=False)
    description = db.Column(db.String(200))
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    @property
    def post_count(self):
        return Post.query.filter_by(category_id=self.id, status='published').count()


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    excerpt = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    content_html = db.Column(db.Text)
    cover_image = db.Column(db.String(500))
    author = db.Column(db.String(50), default='四叶草堂')
    status = db.Column(db.String(20), default='draft')
    view_count = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    published_at = db.Column(db.DateTime)
    
    tags = db.relationship('Tag', secondary='post_tags', backref=db.backref('posts', lazy='dynamic'))


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    slug = db.Column(db.String(40), unique=True, nullable=False)


post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(50))
    role = db.Column(db.String(20), default='editor')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        return self.role == 'admin'


class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    status = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.now)


class FeishuToken(db.Model):
    __tablename__ = 'feishu_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text)
    expires_at = db.Column(db.DateTime)
    feishu_user_id = db.Column(db.String(100))
    feishu_open_id = db.Column(db.String(100))
    feishu_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class FeishuDocument(db.Model):
    __tablename__ = 'feishu_documents'
    id = db.Column(db.Integer, primary_key=True)
    doc_token = db.Column(db.String(100), unique=True, nullable=False)
    doc_type = db.Column(db.String(20), default='docx')
    title = db.Column(db.String(500))
    original_url = db.Column(db.String(500))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='SET NULL'))
    last_sync_at = db.Column(db.DateTime)
    sync_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class FeishuImport(db.Model):
    __tablename__ = 'feishu_imports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doc_token = db.Column(db.String(100), nullable=False)
    doc_title = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


def init_database():
    """初始化数据库"""
    print("开始初始化数据库...")
    
    # 确保data目录存在
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # 创建所有表
    with app.app_context():
        db.create_all()
        print("✓ 数据库表创建完成")
        
        # 创建默认管理员
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@communitygarden.org.cn',
                display_name='管理员',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("✓ 默认管理员账号创建完成")
        
        # 创建默认分类
        default_categories = [
            {'name': '活动资讯', 'slug': 'activities', 'description': '四叶草堂最新活动动态与报道'},
            {'name': '项目动态', 'slug': 'projects', 'description': '社区花园项目进展与成果分享'},
            {'name': '学术研究', 'slug': 'research', 'description': '社区营造领域学术观点与研究'},
            {'name': '媒体报道', 'slug': 'media', 'description': '各大媒体对四叶草堂的报道'},
            {'name': '活动预告', 'slug': 'events', 'description': '即将举办的社区活动信息'},
        ]
        
        for cat_data in default_categories:
            if not Category.query.filter_by(slug=cat_data['slug']).first():
                category = Category(**cat_data)
                db.session.add(category)
                print(f"✓ 分类 '{cat_data['name']}' 创建完成")
        
        db.session.commit()
        print("\n数据库初始化完成！")
        print("\n默认登录信息：")
        print("  用户名: admin")
        print("  密码: admin123")
        print("\n请立即登录后台修改密码！")


if __name__ == '__main__':
    init_database()
