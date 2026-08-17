"""
数据库模型
定义文章、分类、用户等数据模型
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()


class TimestampMixin:
    """时间戳混入类"""
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class Post(db.Model, TimestampMixin):
    """文章模型"""
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    excerpt = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)  # Markdown格式
    content_html = db.Column(db.Text)  # 渲染后的HTML
    cover_image = db.Column(db.String(500))
    author = db.Column(db.String(50), default='四叶草堂')
    status = db.Column(db.String(20), default='draft')  # draft, published, archived
    view_count = db.Column(db.Integer, default=0)
    published_at = db.Column(db.DateTime)
    
    # 外键
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'))
    
    # 关系
    category = db.relationship('Category', backref=db.backref('posts', lazy='dynamic'))
    tags = db.relationship('Tag', secondary='post_tags', backref=db.backref('posts', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Post {self.title}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'excerpt': self.excerpt,
            'content': self.content,
            'cover_image': self.cover_image,
            'author': self.author,
            'status': self.status,
            'view_count': self.view_count,
            'category': self.category.to_dict() if self.category else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None
        }
    
    @property
    def status_text(self):
        """状态文本"""
        status_map = {
            'draft': '草稿',
            'published': '已发布',
            'archived': '已归档'
        }
        return status_map.get(self.status, self.status)


class Category(db.Model, TimestampMixin):
    """分类模型"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(70), unique=True, nullable=False)
    description = db.Column(db.String(200))
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'sort_order': self.sort_order,
            'post_count': self.posts.filter_by(status='published').count()
        }


class User(UserMixin, db.Model, TimestampMixin):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(50))
    role = db.Column(db.String(20), default='editor')  # admin, editor
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        """是否为管理员"""
        return self.role == 'admin'
    
    def to_dict(self):
        """转换为字典（不包含密码）"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'display_name': self.display_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CosTag(db.Model):
    """COS图片标签模型"""
    __tablename__ = 'cos_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#666666')
    sort_order = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<CosTag {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'sort_order': self.sort_order
        }


# 图片-标签关联表（多对多）
cos_image_tags = db.Table('cos_image_tags',
    db.Column('image_key', db.String(500), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('cos_tags.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.now)
)


class CosImageUsage(db.Model):
    """COS图片使用记录"""
    __tablename__ = 'cos_image_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    image_key = db.Column(db.String(500), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='SET NULL'))
    used_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<CosImageUsage {self.image_key[:30]}...>'


class Tag(db.Model):
    """标签模型"""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<Tag {self.name}>'


# 关联表
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class LoginLog(db.Model):
    """登录日志模型"""
    __tablename__ = 'login_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    status = db.Column(db.String(10))  # success, failed
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<LoginLog {self.user_id} {self.status}>'


class FeishuToken(db.Model, TimestampMixin):
    """飞书令牌模型"""
    __tablename__ = 'feishu_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text)
    expires_at = db.Column(db.DateTime)
    feishu_user_id = db.Column(db.String(100))
    feishu_open_id = db.Column(db.String(100))
    feishu_name = db.Column(db.String(100))
    
    user = db.relationship('User', backref=db.backref('feishu_tokens', lazy='dynamic'))
    
    def __repr__(self):
        return f'<FeishuToken {self.feishu_name}>'
    
    def is_expired(self):
        """检查令牌是否过期"""
        from datetime import datetime
        return self.expires_at and self.expires_at < datetime.now()


class FeishuDocument(db.Model, TimestampMixin):
    """飞书文档模型"""
    __tablename__ = 'feishu_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    doc_token = db.Column(db.String(100), unique=True, nullable=False)
    doc_type = db.Column(db.String(20), default='docx')
    title = db.Column(db.String(500))
    original_url = db.Column(db.String(500))
    
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='SET NULL'))
    last_sync_at = db.Column(db.DateTime)
    sync_status = db.Column(db.String(20), default='pending')
    
    post = db.relationship('Post', backref=db.backref('feishu_document', uselist=False))
    
    def __repr__(self):
        return f'<FeishuDocument {self.title}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'doc_token': self.doc_token,
            'doc_type': self.doc_type,
            'title': self.title,
            'original_url': self.original_url,
            'post_id': self.post_id,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'sync_status': self.sync_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FeishuImport(db.Model, TimestampMixin):
    """飞书导入记录模型"""
    __tablename__ = 'feishu_imports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doc_token = db.Column(db.String(100), nullable=False)
    doc_title = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='SET NULL'))
    
    user = db.relationship('User', backref=db.backref('feishu_imports', lazy='dynamic'))
    post = db.relationship('Post', backref=db.backref('feishu_import', uselist=False))
    
    def __repr__(self):
        return f'<FeishuImport {self.doc_title}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'doc_token': self.doc_token,
            'doc_title': self.doc_title,
            'status': self.status,
            'error_message': self.error_message,
            'post_id': self.post_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 工时统计模块 ====================

class Employee(db.Model, TimestampMixin):
    """员工模型"""
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    feishu_user_id = db.Column(db.String(64), unique=True, nullable=False, comment='飞书用户ID')
    name = db.Column(db.String(100), nullable=False, comment='员工姓名')
    email = db.Column(db.String(255), comment='邮箱')
    department = db.Column(db.String(100), comment='部门')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    is_exempt = db.Column(db.Boolean, default=False, comment='是否为例外员工（无需填写工时）')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='关联的登录用户ID')
    
    # 关系
    work_records = db.relationship('WorkHourRecord', backref='employee', lazy='dynamic')
    user = db.relationship('User', backref=db.backref('employee', uselist=False))
    
    def __repr__(self):
        return f'<Employee {self.name}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'feishu_user_id': self.feishu_user_id,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'is_active': self.is_active,
            'is_exempt': self.is_exempt,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WorkHourRecord(db.Model, TimestampMixin):
    """工时记录模型"""
    __tablename__ = 'work_hour_records'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, comment='员工ID')
    year = db.Column(db.Integer, nullable=False, comment='年份')
    month = db.Column(db.Integer, nullable=False, comment='月份')
    total_work_days = db.Column(db.Numeric(4, 1), nullable=False, comment='工作日天数')
    status = db.Column(db.String(20), default='draft', comment='状态: draft/submitted')
    submitted_at = db.Column(db.DateTime, comment='提交时间')
    feishu_record_id = db.Column(db.String(100), comment='飞书记录ID')
    
    # 关系
    items = db.relationship('WorkHourItem', backref='record', lazy='dynamic', cascade='all, delete-orphan')
    
    # 唯一约束：同一员工同一月份只能有一条记录
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'year', 'month', name='unique_employee_month'),
    )
    
    def __repr__(self):
        return f'<WorkHourRecord {self.year}-{self.month} {self.employee_id}>'
    
    @property
    def status_text(self):
        """状态文本"""
        status_map = {
            'draft': '草稿',
            'submitted': '已提交'
        }
        return status_map.get(self.status, self.status)
    
    def to_dict(self, include_items=False):
        """转换为字典"""
        result = {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'year': self.year,
            'month': self.month,
            'total_work_days': float(self.total_work_days) if self.total_work_days else 0,
            'status': self.status,
            'status_text': self.status_text,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'feishu_record_id': self.feishu_record_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_items:
            result['items'] = [item.to_dict() for item in self.items.all()]
        return result


class WorkHourItem(db.Model, TimestampMixin):
    """工时明细模型"""
    __tablename__ = 'work_hour_items'
    
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('work_hour_records.id', ondelete='CASCADE'), nullable=False, comment='工时记录ID')
    project_name = db.Column(db.String(200), nullable=False, comment='项目名称')
    work_days = db.Column(db.Numeric(4, 1), nullable=False, comment='工作天数')
    
    def __repr__(self):
        return f'<WorkHourItem {self.project_name} {self.work_days}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'record_id': self.record_id,
            'project_name': self.project_name,
            'work_days': float(self.work_days) if self.work_days else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WorkHourConfig(db.Model, TimestampMixin):
    """工时系统配置模型"""
    __tablename__ = 'work_hour_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False, comment='配置键')
    config_value = db.Column(db.Text, comment='配置值')
    description = db.Column(db.String(255), comment='配置描述')
    
    def __repr__(self):
        return f'<WorkHourConfig {self.config_key}>'
    
    @classmethod
    def get_value(cls, key, default=None):
        """获取配置值"""
        config = cls.query.filter_by(config_key=key).first()
        return config.config_value if config else default
    
    @classmethod
    def set_value(cls, key, value, description=None):
        """设置配置值"""
        config = cls.query.filter_by(config_key=key).first()
        if config:
            config.config_value = value
            if description:
                config.description = description
        else:
            config = cls(config_key=key, config_value=value, description=description)
            db.session.add(config)
        db.session.commit()
        return config


class ProjectUsage(db.Model, TimestampMixin):
    """项目使用记录模型（用于记录员工历史使用项目）"""
    __tablename__ = 'project_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, comment='员工ID')
    project_name = db.Column(db.String(200), nullable=False, comment='项目名称')
    last_used_at = db.Column(db.DateTime, default=datetime.now, nullable=False, comment='最后使用时间')
    use_count = db.Column(db.Integer, default=1, comment='使用次数')
    
    # 关系
    employee = db.relationship('Employee', backref=db.backref('project_usages', lazy='dynamic'))
    
    # 唯一约束：同一员工同一项目
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'project_name', name='unique_employee_project'),
    )
    
    def __repr__(self):
        return f'<ProjectUsage {self.project_name} by {self.employee_id}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'project_name': self.project_name,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'use_count': self.use_count
        }
