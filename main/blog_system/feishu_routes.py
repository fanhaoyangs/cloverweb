"""
飞书文档导入路由
处理飞书OAuth授权、文档列表、文档导入等功能
"""
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from models import db, Post, Category, FeishuToken, FeishuDocument, FeishuImport
from feishu_config import FeishuConfig
from feishu_auth import feishu_auth
from feishu_api import feishu_doc_api
from feishu_parser import feishu_parser
from utils import generate_slug, render_markdown, create_excerpt

feishu_bp = Blueprint('feishu', __name__, url_prefix='/admin/feishu')


@feishu_bp.route('/')
@login_required
def index():
    """飞书文档导入首页"""
    if not FeishuConfig.is_configured():
        flash('请先配置飞书应用信息', 'error')
        return render_template('admin/feishu-setup.html')
    
    feishu_token = FeishuToken.query.filter_by(user_id=current_user.id).first()
    
    import_history = FeishuImport.query.filter_by(user_id=current_user.id).order_by(
        FeishuImport.created_at.desc()
    ).limit(20).all()
    
    return render_template('admin/feishu-index.html',
                         feishu_token=feishu_token,
                         import_history=import_history)


@feishu_bp.route('/authorize')
@login_required
def authorize():
    """跳转到飞书授权页面"""
    if not FeishuConfig.is_configured():
        flash('请先配置飞书应用信息', 'error')
        return redirect(url_for('feishu.index'))
    
    state = f'user_{current_user.id}'
    auth_url = feishu_auth.config.get_auth_url(state)
    
    return redirect(auth_url)


@feishu_bp.route('/callback')
@login_required
def callback():
    """飞书OAuth回调"""
    code = request.args.get('code')
    state = request.args.get('state', '')
    
    if not code:
        flash('授权失败：未获取到授权码', 'error')
        return redirect(url_for('feishu.index'))
    
    try:
        token_data = feishu_auth.get_user_access_token(code)
        
        user_info = feishu_auth.get_user_info(token_data['access_token'])
        
        feishu_token = FeishuToken.query.filter_by(user_id=current_user.id).first()
        
        if feishu_token:
            feishu_token.access_token = token_data['access_token']
            feishu_token.refresh_token = token_data.get('refresh_token')
            feishu_token.expires_at = datetime.now() + timedelta(seconds=token_data.get('expires_in', 7200))
            feishu_token.feishu_user_id = token_data.get('user_id')
            feishu_token.feishu_open_id = token_data.get('open_id')
            feishu_token.feishu_name = user_info.get('name', '')
        else:
            feishu_token = FeishuToken(
                user_id=current_user.id,
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                expires_at=datetime.now() + timedelta(seconds=token_data.get('expires_in', 7200)),
                feishu_user_id=token_data.get('user_id'),
                feishu_open_id=token_data.get('open_id'),
                feishu_name=user_info.get('name', '')
            )
            db.session.add(feishu_token)
        
        db.session.commit()
        
        flash(f'飞书账号授权成功！欢迎 {user_info.get("name", "")}', 'success')
        
    except Exception as e:
        flash(f'授权失败：{str(e)}', 'error')
    
    return redirect(url_for('feishu.documents'))


@feishu_bp.route('/documents')
@login_required
def documents():
    """显示飞书文档列表"""
    feishu_token = FeishuToken.query.filter_by(user_id=current_user.id).first()
    
    if not feishu_token:
        flash('请先授权飞书账号', 'error')
        return redirect(url_for('feishu.index'))
    
    if feishu_token.is_expired():
        flash('授权已过期，请重新授权', 'error')
        return redirect(url_for('feishu.authorize'))
    
    try:
        user_token = feishu_token.access_token
        folder_token = request.args.get('folder_token', None)
        page_token = request.args.get('page_token', None)
        
        doc_list = feishu_doc_api.get_doc_list(user_token=user_token, folder_token=folder_token, page_token=page_token)
        
        files = doc_list.get('files', [])
        has_more = doc_list.get('has_more', False)
        next_page_token = doc_list.get('page_token')
        
        return render_template('admin/feishu-documents.html',
                             documents=files,
                             has_more=has_more,
                             page_token=next_page_token,
                             current_folder=folder_token,
                             parent_folder=None,
                             folder_name=None)
        
    except Exception as e:
        flash(f'获取文档列表失败：{str(e)}', 'error')
        return redirect(url_for('feishu.index'))


@feishu_bp.route('/import/<doc_token>', methods=['GET', 'POST'])
@login_required
def import_document(doc_token):
    """导入飞书文档"""
    feishu_token = FeishuToken.query.filter_by(user_id=current_user.id).first()
    
    if not feishu_token:
        flash('请先授权飞书账号', 'error')
        return redirect(url_for('feishu.index'))
    
    user_token = feishu_token.access_token
    existing_doc = FeishuDocument.query.filter_by(doc_token=doc_token).first()
    
    if request.method == 'GET':
        try:
            doc_meta = feishu_doc_api.get_doc_meta(doc_token, user_token=user_token)
            doc_title = doc_meta.get('title', '未命名文档')
            
            # 预解析获取表格信息
            doc_data = feishu_doc_api.get_doc_content(doc_token, user_token=user_token)
            sheets_info = feishu_parser.get_sheets_info(doc_data, doc_token, user_token)
            
            categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
            
            return render_template('admin/feishu-import.html',
                                 doc_token=doc_token,
                                 doc_title=doc_title,
                                 categories=categories,
                                 existing_doc=existing_doc,
                                 sheets_info=sheets_info)
            
        except Exception as e:
            flash(f'获取文档信息失败：{str(e)}', 'error')
            return redirect(url_for('feishu.documents'))
    
    if request.method == 'POST':
        import_record = FeishuImport(
            user_id=current_user.id,
            doc_token=doc_token,
            status='pending'
        )
        db.session.add(import_record)
        db.session.commit()
        
        try:
            doc_data = feishu_doc_api.get_doc_content(doc_token, user_token=user_token)
            doc_meta = feishu_doc_api.get_doc_meta(doc_token, user_token=user_token)
            
            # 收集表格列宽配置
            sheets_config = {}
            for key in request.form:
                if key.startswith('sheet_mode_'):
                    sheet_index = key.replace('sheet_mode_', '')
                    mode = request.form.get(key)
                    column_widths_str = request.form.get(f'sheet_column_widths_{sheet_index}', '')
                    
                    if mode != 'default' and column_widths_str:
                        widths = [int(w) for w in column_widths_str.split(',') if w.strip()]
                        if widths:
                            sheets_config[int(sheet_index)] = {
                                'mode': mode,
                                'column_widths': widths
                            }
            
            parsed_data = feishu_parser.parse_document_with_meta(doc_data, doc_token, doc_meta, user_token, sheets_config)
            
            title = request.form.get('title', parsed_data['title'])
            category_id = request.form.get('category_id')
            status = request.form.get('status', 'draft')
            
            content = parsed_data['content']
            content_html = render_markdown(content)
            excerpt = create_excerpt(content)
            slug = generate_slug(title)
            
            if existing_doc and existing_doc.post_id:
                post = Post.query.get(existing_doc.post_id)
                if post:
                    post.title = title
                    post.content = content
                    post.content_html = content_html
                    post.excerpt = excerpt
                    post.category_id = category_id if category_id else None
                    post.status = status
                    
                    if status == 'published' and not post.published_at:
                        post.published_at = datetime.now()
            else:
                post = Post(
                    title=title,
                    slug=slug,
                    content=content,
                    content_html=content_html,
                    excerpt=excerpt,
                    category_id=category_id if category_id else None,
                    status=status,
                    author=current_user.display_name or current_user.username
                )
                
                if status == 'published':
                    post.published_at = datetime.now()
                
                db.session.add(post)
                db.session.flush()
            
            if not existing_doc:
                existing_doc = FeishuDocument(
                    doc_token=doc_token,
                    title=title,
                    post_id=post.id,
                    last_sync_at=datetime.now(),
                    sync_status='success'
                )
                db.session.add(existing_doc)
            else:
                existing_doc.title = title
                existing_doc.post_id = post.id
                existing_doc.last_sync_at = datetime.now()
                existing_doc.sync_status = 'success'
            
            import_record.status = 'success'
            import_record.doc_title = title
            import_record.post_id = post.id
            
            db.session.commit()
            
            flash(f'文档「{title}」导入成功！', 'success')
            return redirect(url_for('admin_post_edit', post_id=post.id))
            
        except Exception as e:
            import_record.status = 'failed'
            import_record.error_message = str(e)
            db.session.commit()
            
            flash(f'导入失败：{str(e)}', 'error')
            return redirect(url_for('feishu.documents'))


@feishu_bp.route('/refresh/<doc_token>')
@login_required
def refresh_document(doc_token):
    """重新同步飞书文档"""
    feishu_doc = FeishuDocument.query.filter_by(doc_token=doc_token).first_or_404()
    
    if not feishu_doc.post_id:
        flash('文档未关联文章，请重新导入', 'error')
        return redirect(url_for('feishu.import_document', doc_token=doc_token))
    
    try:
        doc_data = feishu_doc_api.get_doc_content(doc_token)
        doc_meta = feishu_doc_api.get_doc_meta(doc_token)
        
        parsed_data = feishu_parser.parse_document_with_meta(doc_data, doc_token, doc_meta)
        
        post = Post.query.get(feishu_doc.post_id)
        post.content = parsed_data['content']
        post.content_html = render_markdown(parsed_data['content'])
        post.excerpt = create_excerpt(parsed_data['content'])
        
        feishu_doc.last_sync_at = datetime.now()
        feishu_doc.sync_status = 'success'
        
        db.session.commit()
        
        flash('文档同步成功！', 'success')
        
    except Exception as e:
        feishu_doc.sync_status = 'failed'
        db.session.commit()
        flash(f'同步失败：{str(e)}', 'error')
    
    return redirect(url_for('admin_post_edit', post_id=feishu_doc.post_id))


@feishu_bp.route('/history')
@login_required
def import_history():
    """导入历史"""
    history = FeishuImport.query.filter_by(user_id=current_user.id).order_by(
        FeishuImport.created_at.desc()
    ).paginate(page=request.args.get('page', 1, type=int), per_page=20)
    
    return render_template('admin/feishu-history.html', history=history)


@feishu_bp.route('/disconnect')
@login_required
def disconnect():
    """断开飞书账号连接"""
    feishu_token = FeishuToken.query.filter_by(user_id=current_user.id).first()
    
    if feishu_token:
        db.session.delete(feishu_token)
        db.session.commit()
        flash('已断开飞书账号连接', 'success')
    
    return redirect(url_for('feishu.index'))


@feishu_bp.route('/api/documents')
@login_required
def api_documents():
    """API：获取文档列表"""
    feishu_token = FeishuToken.query.filter_by(user_id=current_user.id).first()
    
    if not feishu_token:
        return jsonify({'code': 401, 'message': '请先授权飞书账号'}), 401
    
    try:
        page_token = request.args.get('page_token')
        doc_list = feishu_doc_api.get_doc_list(page_token=page_token)
        
        return jsonify({
            'code': 200,
            'data': doc_list
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


@feishu_bp.route('/api/import', methods=['POST'])
@login_required
def api_import():
    """API：导入文档"""
    data = request.json
    doc_token = data.get('doc_token')
    title = data.get('title')
    category_id = data.get('category_id')
    status = data.get('status', 'draft')
    
    if not doc_token:
        return jsonify({'code': 400, 'message': '缺少文档token'}), 400
    
    try:
        doc_data = feishu_doc_api.get_doc_content(doc_token)
        doc_meta = feishu_doc_api.get_doc_meta(doc_token)
        
        parsed_data = feishu_parser.parse_document_with_meta(doc_data, doc_token, doc_meta)
        
        title = title or parsed_data['title']
        content = parsed_data['content']
        content_html = render_markdown(content)
        excerpt = create_excerpt(content)
        slug = generate_slug(title)
        
        post = Post(
            title=title,
            slug=slug,
            content=content,
            content_html=content_html,
            excerpt=excerpt,
            category_id=category_id if category_id else None,
            status=status,
            author=current_user.display_name or current_user.username
        )
        
        if status == 'published':
            post.published_at = datetime.now()
        
        db.session.add(post)
        db.session.flush()
        
        feishu_doc = FeishuDocument(
            doc_token=doc_token,
            title=title,
            post_id=post.id,
            last_sync_at=datetime.now(),
            sync_status='success'
        )
        db.session.add(feishu_doc)
        
        import_record = FeishuImport(
            user_id=current_user.id,
            doc_token=doc_token,
            doc_title=title,
            status='success',
            post_id=post.id
        )
        db.session.add(import_record)
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '导入成功',
            'data': {
                'post_id': post.id,
                'title': title
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500
