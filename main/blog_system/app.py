"""
Flask主应用
"""
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import re
import bleach
import markdown
from models import db, Post, Category, User, LoginLog, FeishuToken, FeishuDocument, FeishuImport
from config import FlaskConfig, SiteConfig
from cos_utils import get_uploader
from utils import generate_slug as _generate_slug, render_markdown, create_excerpt
from feishu_routes import feishu_bp
from gallery_routes import gallery_bp
from workhour_routes import workhour_bp


# 初始化应用
app = Flask(__name__, 
    template_folder='templates',
    static_folder='static',
    static_url_path='/blog_static'
)

# 配置
app.config.from_object(FlaskConfig)

# 初始化扩展
db.init_app(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = '请先登录管理员账号'

# 初始化CSRF保护
csrf = CSRFProtect(app)

# 注册飞书导入蓝图
app.register_blueprint(feishu_bp)

# 注册图片库蓝图
app.register_blueprint(gallery_bp)

# 注册工时统计蓝图
app.register_blueprint(workhour_bp, url_prefix='/workhour')


# ============ 辅助函数 ============

def generate_slug(title):
    """生成URL友好的slug，确保唯一性"""
    slug = _generate_slug(title)
    existing = Post.query.filter_by(slug=slug).first()
    if existing:
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return slug


@login_manager.user_loader
def load_user(user_id):
    """加载用户"""
    return User.query.get(int(user_id))


# ============ 前端页面路由 ============

@app.route('/news')
def news_list():
    """资讯列表页"""
    page = request.args.get('page', 1, type=int)
    category_slug = request.args.get('category', None)
    search = request.args.get('search', '')
    
    # 构建查询
    query = Post.query.filter_by(status='published')
    
    if category_slug:
        category = Category.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter_by(category_id=category.id)
    
    if search:
        query = query.filter(Post.title.contains(search) | Post.content.contains(search))
    
    # 按发布时间降序排序
    posts = query.order_by(Post.published_at.desc()).paginate(
        page=page, 
        per_page=SiteConfig.POSTS_PER_PAGE,
        error_out=False
    )
    
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    
    return render_template('news.html', 
                         posts=posts, 
                         categories=categories,
                         current_category=category_slug,
                         search=search)


@app.route('/news/<slug>')
def news_detail(slug):
    """文章详情页"""
    post = Post.query.filter_by(slug=slug, status='published').first_or_404()
    
    # 增加浏览量
    post.view_count += 1
    db.session.commit()
    
    # 获取相关文章（同一分类的最新文章）
    related_posts = []
    if post.category:
        related_posts = Post.query.filter_by(
            category_id=post.category_id, 
            status='published'
        ).filter(Post.id != post.id).order_by(
            Post.published_at.desc()
        ).limit(3).all()
    
    return render_template('article.html', 
                         post=post, 
                         related_posts=related_posts)


@app.route('/')
def index():
    """首页重定向到资讯列表"""
    return redirect(url_for('news_list'))


# ============ 后台管理页面 ============

@app.route('/admin/')
@login_required
def admin_dashboard():
    """管理后台首页"""
    post_count = Post.query.count()
    published_count = Post.query.filter_by(status='published').count()
    draft_count = Post.query.filter_by(status='draft').count()
    category_count = Category.query.count()
    
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         post_count=post_count,
                         published_count=published_count,
                         draft_count=draft_count,
                         category_count=category_count,
                         recent_posts=recent_posts)


@app.route('/admin/login/', methods=['GET', 'POST'])
def admin_login():
    """管理员登录"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('账号已被禁用', 'error')
            else:
                # 记录登录
                user.last_login = datetime.now()
                user.login_count += 1
                db.session.commit()
                
                login_user(user, remember=True)
                
                # 记录登录日志
                log = LoginLog(
                    user_id=user.id,
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string,
                    status='success'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('登录成功', 'success')
                return redirect(url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误', 'error')
            
            # 记录失败的登录尝试
            if user:
                log = LoginLog(
                    user_id=user.id,
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string,
                    status='failed'
                )
                db.session.add(log)
                db.session.commit()
    
    return render_template('admin/login.html')


@app.route('/admin/logout/')
@login_required
def admin_logout():
    """退出登录"""
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/password/', methods=['GET', 'POST'])
@login_required
def admin_password():
    """修改密码"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # 验证当前密码
        if not current_user.check_password(current_password):
            flash('当前密码不正确', 'error')
        elif len(new_password) < 8:
            flash('新密码长度至少8个字符', 'error')
        elif new_password != confirm_password:
            flash('两次输入的密码不一致', 'error')
        else:
            # 更新密码
            current_user.set_password(new_password)
            db.session.commit()
            flash('密码修改成功', 'success')
            return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/password.html')


@app.route('/admin/posts/')
@login_required
def admin_post_list():
    """文章列表"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Post.query
    
    if status:
        query = query.filter_by(status=status)
    
    posts = query.order_by(Post.created_at.desc()).paginate(
        page=page, 
        per_page=SiteConfig.ADMIN_POSTS_PER_PAGE,
        error_out=False
    )
    
    return render_template('admin/post-list.html', posts=posts, current_status=status)


@app.route('/admin/posts/new/', methods=['GET', 'POST'])
@login_required
def admin_post_new():
    """新建文章"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        cover_image = request.form.get('cover_image')
        status = request.form.get('status', 'draft')
        
        if not title or not content:
            flash('标题和内容不能为空', 'error')
        else:
            post = Post(
                title=title,
                slug=generate_slug(title),
                content=content,
                content_html=render_markdown(content),
                excerpt=create_excerpt(content),
                category_id=category_id if category_id else None,
                cover_image=cover_image or None,
                status=status,
                author=current_user.display_name or current_user.username
            )
            
            if status == 'published':
                post.published_at = datetime.now()
            
            db.session.add(post)
            db.session.commit()
            
            flash('文章创建成功', 'success')
            return redirect(url_for('admin_post_list'))
    
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return render_template('admin/post-edit.html', 
                         post=None, 
                         categories=categories,
                         action='new')


@app.route('/admin/posts/<int:post_id>/edit/', methods=['GET', 'POST'])
@login_required
def admin_post_edit(post_id):
    """编辑文章"""
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        cover_image = request.form.get('cover_image')
        status = request.form.get('status', 'draft')
        slug = request.form.get('slug', '').strip()
        
        if not title or not content:
            flash('标题和内容不能为空', 'error')
        else:
            post.title = title
            post.content = content
            post.content_html = render_markdown(content)
            post.excerpt = create_excerpt(content)
            post.category_id = category_id if category_id else None
            post.cover_image = cover_image or None
            post.status = status
            
            # 更新slug（如果用户提供了新的slug且不同于原来的）
            if slug and slug != post.slug:
                # 检查新slug是否已存在（排除自己）
                existing = Post.query.filter(Post.slug == slug, Post.id != post.id).first()
                if existing:
                    flash('该永久链接已被其他文章使用', 'error')
                else:
                    # 验证slug格式
                    if not re.match(r'^[\w\-]+$', slug):
                        flash('永久链接只能包含字母、数字、横线和下划线', 'error')
                    else:
                        post.slug = slug
            
            # 处理发布时间
            if status == 'published' and not post.published_at:
                post.published_at = datetime.now()
            
            db.session.commit()
            
            flash('文章更新成功', 'success')
            return redirect(url_for('admin_post_list'))
    
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return render_template('admin/post-edit.html', 
                         post=post, 
                         categories=categories,
                         action='edit')


@app.route('/admin/posts/<int:post_id>/delete/')
@login_required
def admin_post_delete(post_id):
    """删除文章"""
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('文章已删除', 'success')
    return redirect(url_for('admin_post_list'))


@app.route('/admin/posts/<int:post_id>/publish/')
@login_required
def admin_post_publish(post_id):
    """发布文章"""
    post = Post.query.get_or_404(post_id)
    post.status = 'published'
    post.published_at = datetime.now()
    db.session.commit()
    flash('文章已发布', 'success')
    return redirect(url_for('admin_post_list'))


@app.route('/admin/posts/<int:post_id>/unpublish/')
@login_required
def admin_post_unpublish(post_id):
    """取消发布"""
    post = Post.query.get_or_404(post_id)
    post.status = 'draft'
    db.session.commit()
    flash('文章已取消发布', 'success')
    return redirect(url_for('admin_post_list'))


@app.route('/admin/categories/')
@login_required
def admin_category_list():
    """分类列表"""
    categories = Category.query.order_by(Category.sort_order).all()
    return render_template('admin/category-list.html', categories=categories)


@app.route('/admin/categories/new/', methods=['GET', 'POST'])
@login_required
def admin_category_new():
    """新建分类"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        sort_order = request.form.get('sort_order', 0, type=int)
        
        if not name:
            flash('分类名称不能为空', 'error')
        else:
            slug = re.sub(r'[^\w\s-]', '', name).strip().lower()
            slug = re.sub(r'[\s_]+', '-', slug)
            
            category = Category(
                name=name,
                slug=slug,
                description=description,
                sort_order=sort_order
            )
            db.session.add(category)
            db.session.commit()
            
            flash('分类创建成功', 'success')
            return redirect(url_for('admin_category_list'))
    
    return render_template('admin/category-edit.html', category=None, action='new')


@app.route('/admin/categories/<int:category_id>/edit/', methods=['GET', 'POST'])
@login_required
def admin_category_edit(category_id):
    """编辑分类"""
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        category.sort_order = request.form.get('sort_order', 0, type=int)
        
        # 更新slug
        new_slug = re.sub(r'[^\w\s-]', '', category.name).strip().lower()
        new_slug = re.sub(r'[\s_]+', '-', new_slug)
        
        # 检查slug是否冲突
        existing = Category.query.filter_by(slug=new_slug).first()
        if existing and existing.id != category.id:
            flash('分类别名已存在', 'error')
        else:
            category.slug = new_slug
            db.session.commit()
            flash('分类更新成功', 'success')
            return redirect(url_for('admin_category_list'))
    
    return render_template('admin/category-edit.html', category=category, action='edit')


@app.route('/admin/categories/<int:category_id>/delete/')
@login_required
def admin_category_delete(category_id):
    """删除分类"""
    category = Category.query.get_or_404(category_id)
    
    # 检查是否有文章使用该分类
    if category.posts.count() > 0:
        flash('该分类下有文章，无法删除', 'error')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('分类已删除', 'success')
    
    return redirect(url_for('admin_category_list'))


# ============ API接口 ============

@app.route('/api/upload/image', methods=['POST'])
@login_required
@csrf.exempt
def api_upload_image():
    """图片上传API"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请选择图片文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'code': 400, 'message': '文件名不能为空'}), 400
    
    # 获取COS上传器
    uploader = get_uploader()
    
    if uploader:
        try:
            result = uploader.upload_image(file)
            return jsonify({
                'code': 200,
                'message': '上传成功',
                'data': {
                    'url': result['url'],
                    'key': result['key'],
                    'size': result['size']
                }
            })
        except Exception as e:
            return jsonify({'code': 500, 'message': str(e)}), 500
    else:
        # 降级方案：保存到本地
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return jsonify({'code': 400, 'message': '不支持的文件格式'}), 400
        
        try:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            upload_dir = os.path.join(app.static_folder, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            url = url_for('static', filename=f'uploads/{filename}')
            return jsonify({
                'code': 200,
                'message': '上传成功',
                'data': {'url': url}
            })
        except Exception as e:
            return jsonify({'code': 500, 'message': f'保存文件失败: {str(e)}'}), 500


@app.route('/api/posts/check-slug', methods=['POST'])
def api_check_slug():
    """检查slug是否可用"""
    slug = request.json.get('slug', '').strip()
    post_id = request.json.get('post_id', None)
    
    if not slug:
        return jsonify({'code': 400, 'message': '请输入永久链接'}), 400
    
    # 验证slug格式
    if not re.match(r'^[\w\-]+$', slug):
        return jsonify({'code': 400, 'message': '永久链接只能包含字母、数字、横线和下划线'}), 400
    
    # 检查是否已存在
    query = Post.query.filter_by(slug=slug)
    if post_id:
        query = query.filter(Post.id != int(post_id))
    
    existing = query.first()
    
    if existing:
        return jsonify({'code': 400, 'message': '该永久链接已被使用'}), 400
    
    return jsonify({'code': 200, 'message': '该永久链接可用'})


@app.route('/api/categories', methods=['GET'])
def api_categories():
    """获取分类列表"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return jsonify({
        'code': 200,
        'data': [c.to_dict() for c in categories]
    })


# ============ CLI命令 ============

@app.cli.command('init-db')
def init_db_command():
    """初始化数据库"""
    db.create_all()
    
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
    
    db.session.commit()
    print('数据库初始化完成！')


# ============ 错误处理 ============

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


# ============ 启动应用 ============

if __name__ == '__main__':
    # 初始化目录
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'uploads'), exist_ok=True)
    
    # 运行应用
    port = int(os.environ.get('FLASK_RUN_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
