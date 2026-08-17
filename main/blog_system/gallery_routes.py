"""
图片库路由
提供图片库管理功能
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from models import db, CosTag, cos_image_tags, CosImageUsage
from cos_utils import get_uploader
from datetime import datetime
from urllib.parse import unquote
import logging

logger = logging.getLogger(__name__)

gallery_bp = Blueprint('gallery', __name__, url_prefix='/admin/gallery')


@gallery_bp.route('/')
@login_required
def index():
    """图片库首页"""
    uploader = get_uploader()
    
    tags = CosTag.query.order_by(CosTag.sort_order, CosTag.name).all()
    
    prefix = request.args.get('prefix', '')
    tag_id = request.args.get('tag_id', type=int)
    search = request.args.get('search', '').strip()
    filter_year = request.args.get('year', '')
    filter_month = request.args.get('month', '')
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    # 构建前缀过滤
    if filter_year:
        if filter_month:
            prefix = f"images/{filter_year}/{filter_month}/"
        else:
            prefix = f"images/{filter_year}/"
    
    images = uploader.list_images(prefix=prefix)
    
    # 获取可用年份列表
    all_images = uploader.list_images(prefix='images/')
    available_years = set()
    for img in all_images:
        parts = img['key'].split('/')
        if len(parts) >= 2 and parts[1].isdigit():
            available_years.add(int(parts[1]))
    available_years = sorted(available_years, reverse=True)
    
    if tag_id:
        tagged_keys = db.session.execute(
            db.select(cos_image_tags.c.image_key).where(cos_image_tags.c.tag_id == tag_id)
        ).scalars().all()
        tagged_keys_set = set(tagged_keys)
        images = [img for img in images if img['key'] in tagged_keys_set]
    
    if search:
        images = [img for img in images if search.lower() in img['key'].lower() or search.lower() in img['filename'].lower()]
    
    total = len(images)
    start = (page - 1) * per_page
    images = images[start:start + per_page]
    
    for img in images:
        result = db.session.execute(
            db.select(cos_image_tags.c.tag_id).where(cos_image_tags.c.image_key == img['key'])
        ).scalars().all()
        img['tag_ids'] = result
        img['tags'] = []
        for tid in result:
            tag = CosTag.query.get(tid)
            if tag:
                img['tags'].append(tag.name)
    
    return render_template('admin/gallery/index.html',
                         tags=tags,
                         images=images,
                         page=page,
                         total=total,
                         prefix=prefix,
                         tag_id=tag_id,
                         search=search,
                         filter_year=filter_year,
                         filter_month=filter_month,
                         available_years=available_years)


@gallery_bp.route('/list')
@login_required
def list_images():
    """获取图片列表 API"""
    uploader = get_uploader()
    
    prefix = request.args.get('prefix', '')
    tag_id = request.args.get('tag_id', type=int)
    search = request.args.get('search', '').strip()
    
    images = uploader.list_images(prefix=prefix)
    
    if tag_id:
        tagged_keys = db.session.execute(
            db.select(cos_image_tags.c.image_key).where(cos_image_tags.c.tag_id == tag_id)
        ).scalars().all()
        tagged_keys_set = set(tagged_keys)
        images = [img for img in images if img['key'] in tagged_keys_set]
    
    if search:
        images = [img for img in images if search.lower() in img['filename'].lower()]
    
    for img in images:
        result = db.session.execute(
            db.select(cos_image_tags.c.tag_id).where(cos_image_tags.c.image_key == img['key'])
        ).scalars().all()
        img['tag_ids'] = result
        img['tags'] = []
        for tid in result:
            tag = CosTag.query.get(tid)
            if tag:
                img['tags'].append(tag.name)
    
    return jsonify({
        'images': images,
        'total': len(images)
    })


@gallery_bp.route('/tags', methods=['GET', 'POST'])
@login_required
def manage_tags():
    """标签管理"""
    if request.method == 'GET':
        tags = CosTag.query.order_by(CosTag.sort_order, CosTag.name).all()
        return render_template('admin/gallery/tags.html', tags=tags)
    
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#666666')
    
    if not name:
        flash('标签名不能为空', 'error')
        return redirect(url_for('gallery.manage_tags'))
    
    existing = CosTag.query.filter_by(name=name).first()
    if existing:
        flash('标签已存在', 'error')
        return redirect(url_for('gallery.manage_tags'))
    
    tag = CosTag(name=name, color=color)
    db.session.add(tag)
    db.session.commit()
    
    flash('标签创建成功', 'success')
    return redirect(url_for('gallery.manage_tags'))


@gallery_bp.route('/tag/<int:tag_id>/edit', methods=['POST'])
@login_required
def edit_tag(tag_id):
    """编辑标签"""
    tag = CosTag.query.get(tag_id)
    if not tag:
        return jsonify({'success': False, 'message': '标签不存在'})
    
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', '#666666')
    
    if not name:
        return jsonify({'success': False, 'message': '标签名不能为空'})
    
    existing = CosTag.query.filter(CosTag.name == name, CosTag.id != tag_id).first()
    if existing:
        return jsonify({'success': False, 'message': '标签名已存在'})
    
    tag.name = name
    tag.color = color
    db.session.commit()
    
    return jsonify({'success': True})


@gallery_bp.route('/tag/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    """删除标签"""
    tag = CosTag.query.get(tag_id)
    if not tag:
        return jsonify({'success': False, 'message': '标签不存在'})
    
    db.session.execute(
        db.delete(cos_image_tags).where(cos_image_tags.c.tag_id == tag_id)
    )
    
    db.session.delete(tag)
    db.session.commit()
    
    return jsonify({'success': True})


@gallery_bp.route('/image/<path:image_key>/tags', methods=['GET', 'POST'])
@login_required
def image_tags(image_key):
    """获取或设置图片标签"""
    image_key = unquote(image_key)
    
    if request.method == 'GET':
        result = db.session.execute(
            db.select(cos_image_tags.c.tag_id).where(cos_image_tags.c.image_key == image_key)
        ).scalars().all()
        
        tag_names = []
        for tid in result:
            tag = CosTag.query.get(tid)
            if tag:
                tag_names.append(tag.name)
        
        return jsonify({'tags': tag_names})
    
    tag_ids = request.form.getlist('tag_ids', [])
    
    db.session.execute(
        db.delete(cos_image_tags).where(cos_image_tags.c.image_key == image_key)
    )
    
    for tag_id in tag_ids:
        try:
            tag_id = int(tag_id)
            tag = CosTag.query.get(tag_id)
            if tag:
                db.session.execute(
                    cos_image_tags.insert().values(image_key=image_key, tag_id=tag_id)
                )
        except (ValueError, TypeError):
            continue
    
    db.session.commit()
    
    return jsonify({'success': True})


@gallery_bp.route('/image/<path:image_key>/use', methods=['POST'])
@login_required
def record_usage(image_key):
    """记录图片使用"""
    image_key = unquote(image_key)
    usage = CosImageUsage(image_key=image_key)
    db.session.add(usage)
    db.session.commit()
    
    return jsonify({'success': True})


@gallery_bp.route('/select')
@login_required
def select():
    """图片选择器（用于编辑器）"""
    uploader = get_uploader()
    
    prefix = request.args.get('prefix', '')
    tag_id = request.args.get('tag_id', type=int)
    search = request.args.get('search', '').strip()
    
    images = uploader.list_images(prefix=prefix)
    
    if tag_id:
        tagged_keys = db.session.execute(
            db.select(cos_image_tags.c.image_key).where(cos_image_tags.c.tag_id == tag_id)
        ).scalars().all()
        tagged_keys_set = set(tagged_keys)
        images = [img for img in images if img['key'] in tagged_keys_set]
    
    if search:
        images = [img for img in images if search.lower() in img['filename'].lower()]
    
    for img in images:
        result = db.session.execute(
            db.select(cos_image_tags.c.tag_id).where(cos_image_tags.c.image_key == img['key'])
        ).scalars().all()
        img['tag_ids'] = result
        img['tags'] = []
        for tid in result:
            tag = CosTag.query.get(tid)
            if tag:
                img['tags'].append(tag.name)
    
    tags = CosTag.query.order_by(CosTag.sort_order, CosTag.name).all()
    
    return render_template('admin/gallery/select.html',
                         images=images,
                         tags=tags,
                         prefix=prefix,
                         tag_id=tag_id,
                         search=search)
