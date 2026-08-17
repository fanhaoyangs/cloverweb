"""
工时统计模块路由
提供工时填报、管理后台等功能
"""
import os
import json
from functools import wraps
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file, current_app, abort
from flask_login import login_required, current_user
from werkzeug.security import safe_join

from models import db, Employee, WorkHourRecord, WorkHourItem, WorkHourConfig, User, ProjectUsage, FeishuToken
from feishu_api import FeishuAPI


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login'))
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

workhour_bp = Blueprint('workhour', __name__, 
                       template_folder='templates/workhour',
                       static_folder='static/workhour',
                       static_url_path='/workhour_static')


def get_feishu_api():
    """获取飞书API实例"""
    return FeishuAPI()


def get_work_days_in_month(year, month):
    """计算指定月份的工作日天数（周一至周五，排除法定节假日）"""
    import calendar
    
    # 简单实现：计算该月周一至周五的天数
    # 实际生产环境应接入节假日API
    cal = calendar.Calendar()
    work_days = 0
    
    for day in cal.itermonthdays(year, month):
        if day != 0:
            # 获取星期几（0=周一，6=周日）
            date = datetime(year, month, day).weekday()
            if date < 5:  # 周一至周五
                work_days += 1
    
    return float(work_days)


def get_config(key, default=''):
    """获取配置值"""
    return WorkHourConfig.get_value(key, default)


def get_current_employee():
    """获取当前登录用户对应的员工记录"""
    if not current_user.is_authenticated:
        return None
    
    # 先从 FeishuToken 获取用户的飞书信息
    feishu_token = FeishuToken.query.filter_by(user_id=current_user.id).first()
    
    if feishu_token:
        # 通过飞书 open_id 匹配员工
        if feishu_token.feishu_open_id:
            employee = Employee.query.filter_by(
                feishu_user_id=feishu_token.feishu_open_id,
                is_active=True
            ).first()
            if employee:
                return employee
        
        # 通过飞书姓名匹配员工
        if feishu_token.feishu_name:
            employee = Employee.query.filter_by(
                name=feishu_token.feishu_name,
                is_active=True
            ).first()
            if employee:
                return employee
    
    # 如果员工表为空，创建一个默认员工
    if Employee.query.count() == 0:
        employee = Employee(
            feishu_user_id=feishu_token.feishu_open_id if feishu_token and feishu_token.feishu_open_id else current_user.username,
            name=feishu_token.feishu_name if feishu_token and feishu_token.feishu_name else current_user.username,
            email=current_user.email or '',
            department='',
            is_active=True
        )
        db.session.add(employee)
        db.session.commit()
        return employee
    
    return None


def record_project_usage(employee_id, project_name):
    """记录员工使用过的项目（用于常用项目推荐）"""
    if not employee_id or not project_name:
        return
    
    try:
        # 查找是否已存在
        usage = ProjectUsage.query.filter_by(
            employee_id=employee_id,
            project_name=project_name
        ).first()
        
        if usage:
            # 更新使用记录
            usage.last_used_at = datetime.now()
            usage.use_count += 1
        else:
            # 创建新记录
            usage = ProjectUsage(
                employee_id=employee_id,
                project_name=project_name,
                last_used_at=datetime.now(),
                use_count=1
            )
            db.session.add(usage)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning(f'记录项目使用失败: {e}')


def get_employee_frequent_projects(employee_id, limit=5):
    """获取员工常用的项目列表"""
    if not employee_id:
        return []
    
    # 查询最近使用且使用次数最多的项目
    usages = ProjectUsage.query.filter_by(employee_id=employee_id)\
        .order_by(ProjectUsage.use_count.desc(), ProjectUsage.last_used_at.desc())\
        .limit(limit)\
        .all()
    
    return [u.project_name for u in usages]


# ==================== 飞书登录路由 ====================

@workhour_bp.route('/feishu_login')
def feishu_login():
    """跳转到飞书授权页面"""
    from feishu_config import FeishuWorkhourConfig
    
    if not FeishuWorkhourConfig.is_configured():
        flash('飞书应用未配置', 'error')
        return redirect(url_for('workhour.not_configured'))
    
    # 生成随机 state 用于安全验证
    import secrets
    state = secrets.token_urlsafe(16)
    
    # 回调 URL - 强制使用 HTTPS
    callback_url = request.host_url.replace('http://', 'https://')
    callback_url = callback_url.rstrip('/') + '/workhour/feishu/callback'
    
    # 获取授权 URL
    auth_url = FeishuWorkhourConfig.get_auth_url(callback_url, state)
    
    return redirect(auth_url)


@workhour_bp.route('/feishu/callback')
def feishu_callback():
    """飞书 OAuth 回调"""
    from feishu_auth import feishu_workhour_auth
    import logging
    
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    logger.debug(f'飞书回调 - code: {code}, state: {state}')
    
    if not code:
        flash('授权失败：未获取到授权码', 'error')
        logger.error('未获取到授权码')
        return redirect(url_for('workhour.index'))
    
    try:
        # 获取用户访问令牌
        token_data = feishu_workhour_auth.get_user_access_token(code)
        open_id = token_data.get('open_id')
        access_token = token_data.get('access_token')
        
        logger.debug(f'获取令牌成功 - open_id: {open_id}')
        
        # 获取用户信息
        user_info = feishu_workhour_auth.get_user_info(access_token)
        name = user_info.get('name', '')
        
        logger.debug(f'获取用户信息成功 - name: {name}')
        
        # 打印所有员工信息，用于调试
        all_employees = Employee.query.all()
        logger.debug(f'所有员工: {[(emp.id, emp.name, emp.feishu_user_id, emp.is_active) for emp in all_employees]}')
        
        # 检查数据库中的员工数量
        employee_count = Employee.query.count()
        logger.debug(f'员工总数: {employee_count}')
        
        # 检查数据类型
        logger.debug(f'open_id 类型: {type(open_id)}, 值: {open_id}, 长度: {len(open_id) if open_id else 0}')
        logger.debug(f'name 类型: {type(name)}, 值: {name}, 长度: {len(name) if name else 0}')
        
        # 检查数据库连接状态
        from sqlalchemy import text
        try:
            db.session.execute(text('SELECT 1'))
            logger.debug('数据库连接正常')
        except Exception as e:
            logger.error(f'数据库连接异常: {e}')
        
        # 通过 open_id 查找员工（包括未激活的）
        logger.debug(f'尝试通过 open_id 查找: {open_id}')
        # 打印SQL查询
        from sqlalchemy import inspect
        query = Employee.query.filter_by(feishu_user_id=open_id)
        logger.debug(f'OpenID查询SQL: {str(query.statement)}')
        employee = query.first()
        logger.debug(f'通过 open_id 查找结果: {employee}')
        
        if not employee:
            # 通过姓名查找（包括未激活的）
            logger.debug(f'尝试通过姓名查找: {name}')
            query = Employee.query.filter_by(name=name)
            logger.debug(f'姓名查询SQL: {str(query.statement)}')
            employee = query.first()
            logger.debug(f'通过姓名查找结果: {employee}')
        
        if not employee:
            # 尝试不区分大小写的姓名查找（包括未激活的）
            logger.debug(f'尝试不区分大小写的姓名查找: {name}')
            from sqlalchemy import func
            query = Employee.query.filter(
                func.lower(Employee.name) == func.lower(name)
            )
            logger.debug(f'不区分大小写姓名查询SQL: {str(query.statement)}')
            employee = query.first()
            logger.debug(f'不区分大小写的姓名查找结果: {employee}')
        
        if not employee:
            # 尝试模糊匹配姓名（包括未激活的）
            logger.debug(f'尝试模糊匹配姓名: {name}')
            query = Employee.query.filter(
                Employee.name.like(f'%{name}%')
            )
            logger.debug(f'模糊匹配姓名查询SQL: {str(query.statement)}')
            employee = query.first()
            logger.debug(f'模糊匹配姓名查找结果: {employee}')
        
        if not employee:
            # 尝试直接查询所有员工（包括未激活的）
            logger.debug('尝试查询所有员工')
            all_employees = Employee.query.all()
            logger.debug(f'所有员工: {[(emp.id, emp.name, emp.feishu_user_id, emp.is_active) for emp in all_employees]}')
            
            # 手动匹配
            for emp in all_employees:
                logger.debug(f'比较 - 数据库: name={emp.name}, feishu_user_id={emp.feishu_user_id}, is_active={emp.is_active}; 飞书: name={name}, open_id={open_id}')
                logger.debug(f'name 匹配: {emp.name == name}, feishu_user_id 匹配: {emp.feishu_user_id == open_id}')
                logger.debug(f'name 长度: {len(emp.name)} vs {len(name)}, feishu_user_id 长度: {len(emp.feishu_user_id)} vs {len(open_id)}')
                
                # 检查是否有空格或特殊字符
                if emp.name.strip() == name.strip():
                    logger.debug(f'姓名去除空格后匹配: {emp.name.strip()} == {name.strip()}')
                if emp.feishu_user_id.strip() == open_id.strip():
                    logger.debug(f'飞书用户ID去除空格后匹配: {emp.feishu_user_id.strip()} == {open_id.strip()}')
        
        if not employee:
            flash(f'未找到对应的员工信息，请联系管理员。您的飞书账号：{name} ({open_id})', 'warning')
            logger.warning(f'未找到员工 - name: {name}, open_id: {open_id}')
            return redirect(url_for('workhour.not_configured', name=name, open_id=open_id))
        
        # 员工信息写入 session
        from flask import session
        session['feishu_open_id'] = open_id
        session['feishu_name'] = name
        session['employee_id'] = employee.id
        session.permanent = True
        session.modified = True  # 确保session被保存
        
        logger.debug(f'登录成功 - employee_id: {employee.id}, name: {employee.name}')
        flash(f'登录成功！欢迎 {employee.name}', 'success')
        return redirect(url_for('workhour.index'))
        
    except Exception as e:
        flash(f'授权失败：{str(e)}', 'error')
        logger.error(f'授权失败: {e}', exc_info=True)
        return redirect(url_for('workhour.index'))


@workhour_bp.route('/logout')
def logout():
    """退出登录"""
    from flask import session
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('workhour.index'))


@workhour_bp.route('/not_configured')
def not_configured():
    """飞书应用未配置页面"""
    from feishu_config import FeishuWorkhourConfig
    
    # 获取飞书用户信息（如果有）
    name = request.args.get('name')
    open_id = request.args.get('open_id')
    
    return render_template('workhour/not_configured.html',
                         app_configured=FeishuWorkhourConfig.is_configured(),
                         name=name,
                         open_id=open_id)


# ==================== 工时填报页面 ====================

@workhour_bp.route('/')
def index():
    """工时填报首页"""
    from flask import session
    
    # 检查 session 中是否有员工信息
    employee_id = session.get('employee_id')
    employee = None
    
    if employee_id:
        employee = Employee.query.get(employee_id)
    
    if not employee:
        # 未登录，跳转到飞书授权
        return redirect(url_for('workhour.feishu_login'))
    
    # 获取当前年月
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    
    # 计算该月工作日天数
    total_work_days = get_work_days_in_month(year, month)
    
    # 获取该月的工时记录
    items = []
    allocated_days = 0
    remaining_days = total_work_days
    
    record = WorkHourRecord.query.filter_by(
        employee_id=employee.id,
        year=year,
        month=month
    ).first()

    if record:
        for item in record.items.all():
            allocated_days += float(item.work_days)
            items.append(item.to_dict())
        record_status = record.status
    else:
        record_status = None

    remaining_days = round(total_work_days - allocated_days, 1)

    return render_template('workhour/index.html',
                         employee=employee,
                         year=year,
                         month=month,
                         total_work_days=total_work_days,
                         remaining_days=remaining_days,
                         items=items,
                         record_status=record_status)


@workhour_bp.route('/api/projects', methods=['GET'])
def get_projects():
    """获取项目列表（从飞书多维表格获取），包含常用项目和全部项目"""
    from flask import session
    
    employee_id = session.get('employee_id')
    
    try:
        feishu_api = get_feishu_api()
        all_projects = feishu_api.get_project_list()
        
        if not all_projects:
            all_projects = [
                '社区花园营造项目 - 浦东新区',
                '社区花园营造项目 - 静安区',
                '社区花园营造项目 - 徐汇区',
                '社区花园营造项目 - 闵行区',
                '种子图书馆项目',
                '社区花园营造项目 - 长宁区',
                '社区花园营造项目 - 黄浦区',
                '社区花园营造项目 - 杨浦区',
            ]
        
        # 获取当前员工的常用项目
        frequent_projects = get_employee_frequent_projects(employee_id, limit=5) if employee_id else []
        
        # 常用项目：从全部项目中筛选出常用的，并保持顺序
        frequent_list = [p for p in frequent_projects if p in all_projects]
        
        return jsonify({
            'code': 200, 
            'data': {
                'all_projects': all_projects,
                'frequent_projects': frequent_list
            }
        })
            
    except Exception as e:
        # 出错时返回示例数据
        all_projects = [
            '社区花园营造项目 - 浦东新区',
            '社区花园营造项目 - 静安区',
            '社区花园营造项目 - 徐汇区',
            '社区花园营造项目 - 闵行区',
            '种子图书馆项目',
        ]
        return jsonify({
            'code': 200, 
            'data': {
                'all_projects': all_projects,
                'frequent_projects': []
            },
            'warning': str(e)
        })


@workhour_bp.route('/api/save', methods=['POST'])
def save_workhour():
    """保存工时数据（草稿或提交）"""
    from flask import session
    
    employee_id = session.get('employee_id')
    if not employee_id:
        return jsonify({'code': 401, 'message': '请先登录'})
    
    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({'code': 400, 'message': '未找到员工信息'})
    
    try:
        data = request.get_json()
        year = data.get('year')
        month = data.get('month')
        total_work_days = data.get('total_work_days')
        items = data.get('items', [])
        
        # 查找或创建工时记录
        record = WorkHourRecord.query.filter_by(
            employee_id=employee.id,
            year=year,
            month=month
        ).first()
        
        if not record:
            record = WorkHourRecord(
                employee_id=employee.id,
                year=year,
                month=month,
                total_work_days=total_work_days,
                status='draft'
            )
            db.session.add(record)
            db.session.flush()
        else:
            record.total_work_days = total_work_days
        
        # 删除旧的明细
        WorkHourItem.query.filter_by(record_id=record.id).delete()
        
        # 添加新的明细
        for item in items:
            work_item = WorkHourItem(
                record_id=record.id,
                project_name=item.get('project_name'),
                work_days=Decimal(str(item.get('work_days')))
            )
            db.session.add(work_item)
            
            # 记录项目使用（用于常用项目推荐）
            record_project_usage(employee.id, item.get('project_name'))
        
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '保存成功', 'record_id': record.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'保存失败: {str(e)}'})


@workhour_bp.route('/api/submit', methods=['POST'])
def submit_workhour():
    """提交工时到飞书多维表格"""
    from flask import session
    
    employee_id = session.get('employee_id')
    if not employee_id:
        return jsonify({'code': 401, 'message': '请先登录'})
    
    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({'code': 400, 'message': '未找到员工信息'})
    
    try:
        data = request.get_json()
        year = data.get('year')
        month = data.get('month')
        
        # 获取工时记录
        record = WorkHourRecord.query.filter_by(
            employee_id=employee.id,
            year=year,
            month=month
        ).first()
        
        if not record:
            return jsonify({'code': 400, 'message': '请先保存工时数据'})
        
        if record.items.count() == 0:
            return jsonify({'code': 400, 'message': '请至少添加一个项目工时'})
        
        # 计算已分配天数
        allocated_days = sum(float(item.work_days) for item in record.items.all())
        total_days = float(record.total_work_days)

        # 更新记录状态
        record.status = 'submitted'
        record.submitted_at = datetime.now()

        db.session.commit()
        
        return jsonify({
            'code': 200, 
            'message': '提交成功',
            'data': record.to_dict(include_items=True)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'提交失败: {str(e)}'})


@workhour_bp.route('/api/status/<int:year>/<int:month>', methods=['GET'])
def get_status(year, month):
    """获取指定月份的填报状态"""
    employee = get_current_employee()
    if not employee:
        return jsonify({'code': 200, 'data': {
            'submitted': False,
            'total_work_days': 0,
            'allocated_days': 0,
            'items': []
        }})
    
    record = WorkHourRecord.query.filter_by(
        employee_id=employee.id,
        year=year,
        month=month
    ).first()
    
    if not record:
        return jsonify({'code': 200, 'data': {
            'submitted': False,
            'total_work_days': get_work_days_in_month(year, month),
            'allocated_days': 0,
            'items': []
        }})
    
    allocated_days = sum(float(item.work_days) for item in record.items.all())
    
    return jsonify({'code': 200, 'data': {
        'submitted': record.status == 'submitted',
        'status': record.status,
        'total_work_days': float(record.total_work_days),
        'allocated_days': allocated_days,
        'items': [item.to_dict() for item in record.items.all()]
    }})


# ==================== 管理后台 ====================

@workhour_bp.route('/admin/')
@login_required
@admin_required
def admin_index():
    """管理后台首页"""
    return render_template('workhour/admin/index.html')


@workhour_bp.route('/admin/employees/')
@login_required
@admin_required
def admin_employees():
    """员工管理页面"""
    employees = Employee.query.order_by(Employee.is_exempt.asc(), Employee.name).all()
    return render_template('workhour/admin/employees.html', employees=employees)


@workhour_bp.route('/admin/api/employees', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_api_employees():
    """员工管理API"""
    if request.method == 'GET':
        employees = Employee.query.order_by(Employee.is_exempt.asc(), Employee.name).all()
        return jsonify({'code': 200, 'data': [e.to_dict() for e in employees]})
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # 验证
        if not data.get('name'):
            return jsonify({'code': 400, 'message': '员工姓名不能为空'})
        if not data.get('feishu_user_id'):
            return jsonify({'code': 400, 'message': '飞书用户ID不能为空'})
        
        # 检查是否已存在
        existing = Employee.query.filter_by(feishu_user_id=data['feishu_user_id']).first()
        if existing:
            return jsonify({'code': 400, 'message': '该飞书用户ID已存在'})
        
        employee = Employee(
            feishu_user_id=data['feishu_user_id'],
            name=data['name'],
            email=data.get('email', ''),
            department=data.get('department', ''),
            is_active=data.get('is_active', True),
            is_exempt=data.get('is_exempt', False)
        )
        db.session.add(employee)
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '添加成功', 'data': employee.to_dict()})


@workhour_bp.route('/admin/api/employees/<int:id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def admin_api_employee(id):
    """编辑/删除员工"""
    employee = Employee.query.get_or_404(id)
    
    if request.method == 'PUT':
        data = request.get_json()
        
        if data.get('name'):
            employee.name = data['name']
        if 'email' in data:
            employee.email = data.get('email', '')
        if 'department' in data:
            employee.department = data.get('department', '')
        if 'is_active' in data:
            employee.is_active = data['is_active']
        if 'is_exempt' in data:
            employee.is_exempt = data['is_exempt']
        
        db.session.commit()
        return jsonify({'code': 200, 'message': '更新成功', 'data': employee.to_dict()})
    
    elif request.method == 'DELETE':
        db.session.delete(employee)
        db.session.commit()
        return jsonify({'code': 200, 'message': '删除成功'})


@workhour_bp.route('/admin/api/employees/preview-sync', methods=['GET'])
@login_required
@admin_required
def admin_preview_sync_employees():
    """预览从飞书同步的新员工（不在本地列表中的）"""
    try:
        feishu_api = get_feishu_api()
        feishu_users = feishu_api.get_contact_users()

        if not feishu_users:
            return jsonify({'code': 400, 'message': '获取飞书通讯录失败，请检查飞书应用权限'})

        # 获取本地已有的飞书用户ID
        existing_ids = {e.feishu_user_id for e in Employee.query.all()}

        # 筛选出不在本地列表中的用户
        new_users = []
        for user in feishu_users:
            feishu_user_id = user.get('user_id')
            if feishu_user_id and feishu_user_id not in existing_ids:
                new_users.append({
                    'user_id': feishu_user_id,
                    'name': user.get('name', ''),
                    'email': user.get('email', ''),
                    'department': user.get('department', '')
                })

        return jsonify({
            'code': 200,
            'data': new_users,
            'total': len(new_users)
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'预览失败: {str(e)}'})


@workhour_bp.route('/admin/api/employees/sync', methods=['POST'])
@login_required
@admin_required
def admin_sync_employees():
    """从飞书通讯录同步员工（仅导入选中的用户）"""
    try:
        data = request.get_json()
        selected_users = data.get('users', [])

        if not selected_users:
            return jsonify({'code': 400, 'message': '请选择要导入的员工'})

        synced_count = 0
        for user in selected_users:
            feishu_user_id = user.get('user_id')
            name = user.get('name', '')
            email = user.get('email', '')
            department = user.get('department', '')

            if not feishu_user_id or not name:
                continue

            # 检查是否已存在
            existing = Employee.query.filter_by(feishu_user_id=feishu_user_id).first()

            if existing:
                existing.name = name
                existing.email = email or existing.email
                existing.department = department or existing.department
            else:
                employee = Employee(
                    feishu_user_id=feishu_user_id,
                    name=name,
                    email=email,
                    department=department,
                    is_active=True,
                    is_exempt=False
                )
                db.session.add(employee)
            synced_count += 1

        db.session.commit()

        return jsonify({
            'code': 200,
            'message': f'同步完成！新增/更新 {synced_count} 人',
            'data': {'synced': synced_count}
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'同步失败: {str(e)}'})


@workhour_bp.route('/admin/status/')
@login_required
@admin_required
def admin_status():
    """提交状态监控页面"""
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    
    # 获取所有需要填报的员工（已激活且非例外员工）
    employees = Employee.query.filter_by(is_active=True, is_exempt=False).all()

    # 获取已提交记录
    submitted_records = WorkHourRecord.query.filter_by(
        year=year,
        month=month,
        status='submitted'
    ).order_by(WorkHourRecord.submitted_at.asc()).all()
    submitted_employee_ids = {r.employee_id for r in submitted_records}

    # 构建状态列表
    status_list = []
    for emp in employees:
        record = next((r for r in submitted_records if r.employee_id == emp.id), None)
        status_list.append({
            'employee': emp.to_dict(),
            'submitted': emp.id in submitted_employee_ids,
            'record': record
        })

    # 已提交的按提交时间排序（最先提交的在前），未提交的放在后面
    status_list.sort(key=lambda x: (
        0 if x['submitted'] else 1,
        x['record'].submitted_at if x['submitted'] and x['record'] and x['record'].submitted_at else datetime.max
    ))

    # 统计数据
    total = len(employees)
    submitted = len([s for s in status_list if s['submitted']])
    pending = total - submitted
    
    return render_template('workhour/admin/status.html',
                         status_list=status_list,
                         year=year,
                         month=month,
                         total=total,
                         submitted=submitted,
                         pending=pending)


@workhour_bp.route('/admin/summary/')
@login_required
@admin_required
def admin_summary():
    """月度汇总表页面"""
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    
    return render_template('workhour/admin/summary.html',
                         year=year,
                         month=month)


@workhour_bp.route('/admin/api/summary/<int:year>/<int:month>', methods=['GET'])
@login_required
@admin_required
def admin_api_summary(year, month):
    """获取月度汇总数据"""
    # 获取所有已提交的工时记录
    records = WorkHourRecord.query.filter_by(
        year=year,
        month=month,
        status='submitted'
    ).all()
    
    # 构建汇总数据
    summary_data = []
    month_str = f'{year}年{month}月'
    for record in records:
        employee_name = record.employee.name if record.employee else '未知'
        for item in record.items.all():
            summary_data.append({
                'month': month_str,
                'employee_name': employee_name,
                'project_name': item.project_name,
                'work_days': float(item.work_days)
            })

    # 按月份、员工姓名和项目名称排序
    summary_data.sort(key=lambda x: (x['month'], x['employee_name'], x['project_name']))
    
    return jsonify({
        'code': 200,
        'data': summary_data,
        'year': year,
        'month': month
    })


@workhour_bp.route('/admin/api/export/<int:year>/<int:month>')
@login_required
@admin_required
def admin_api_export(year, month):
    """导出月度汇总表"""
    import io
    import csv
    
    # 获取汇总数据
    records = WorkHourRecord.query.filter_by(
        year=year,
        month=month,
        status='submitted'
    ).all()
    
    # 构建数据
    data = []
    for record in records:
        employee_name = record.employee.name if record.employee else '未知'
        month_str = f'{year}年{month}月'
        for item in record.items.all():
            data.append([
                month_str,
                employee_name,
                item.project_name,
                f'{float(item.work_days):.1f}'
            ])

    # 按月份、员工姓名和项目名称排序
    data.sort(key=lambda x: (x[0], x[1], x[2]))

    # 创建CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['月份', '员工姓名', '项目名称', '工时分配（天）'])
    writer.writerows(data)

    # 生成文件名
    filename = f'工时汇总_{year}年{month}月.csv'
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@workhour_bp.route('/admin/config/')
@login_required
@admin_required
def admin_config():
    """飞书配置页面 - 显示和编辑配置"""
    from feishu_config import FeishuWorkhourConfig
    
    # 从数据库读取配置（优先），如果数据库没有则使用环境变量
    bitable_app_token = get_config('bitable_app_token') or FeishuWorkhourConfig.BITABLE_APP_TOKEN
    project_table_id = get_config('project_table_id') or FeishuWorkhourConfig.PROJECT_TABLE_ID
    workhour_table_id = get_config('workhour_table_id') or FeishuWorkhourConfig.WORKHOUR_TABLE_ID
    bot_open_id = get_config('bot_open_id') or FeishuWorkhourConfig.BOT_OPEN_ID
    
    config = {
        # 飞书应用配置（环境变量，只读）
        'app_id': FeishuWorkhourConfig.APP_ID,
        'app_secret': FeishuWorkhourConfig.APP_SECRET,
        'app_configured': FeishuWorkhourConfig.is_configured(),
        
        # 多维表格配置（数据库优先）
        'bitable_app_token': bitable_app_token,
        'project_table_id': project_table_id,
        'workhour_table_id': workhour_table_id,
        'tables_configured': bool(bitable_app_token and project_table_id and workhour_table_id),
        
        # Bot配置（数据库优先）
        'bot_open_id': bot_open_id,
        
        # 通知日期
        'notification_day': get_config('notification_day', '28'),
        
        # 配置完整性检查
        'is_complete': bool(FeishuWorkhourConfig.is_configured() and bitable_app_token and project_table_id and workhour_table_id),
        'has_partial': bool(bitable_app_token or project_table_id or workhour_table_id or bot_open_id)
    }
    return render_template('workhour/admin/config.html', config=config)


@workhour_bp.route('/admin/api/config', methods=['POST'])
@login_required
@admin_required
def admin_api_config():
    """保存飞书配置到数据库"""
    data = request.get_json()
    
    config_mapping = {
        'bitable_app_token': '多维表格 App Token',
        'project_table_id': '项目信息汇总表ID',
        'workhour_table_id': '工时统计表ID',
        'bot_open_id': '机器人Open ID',
        'notification_day': '每月通知日期'
    }
    
    for key, desc in config_mapping.items():
        if key in data:
            WorkHourConfig.set_value(key, str(data[key]), desc)
    
    return jsonify({'code': 200, 'message': '配置保存成功'})


@workhour_bp.route('/admin/api/test-connection', methods=['POST'])
@login_required
@admin_required
def admin_api_test_connection():
    """测试飞书多维表格连接"""
    data = request.get_json()
    
    bitable_app_token = data.get('bitable_app_token')
    project_table_id = data.get('project_table_id')
    
    if not bitable_app_token or not project_table_id:
        return jsonify({'code': 400, 'message': '缺少必要参数'})
    
    try:
        from feishu_api import FeishuAPI
        from feishu_config import FeishuWorkhourConfig
        import requests
        
        # 获取访问令牌
        from feishu_auth import feishu_workhour_auth
        token = feishu_workhour_auth.get_tenant_access_token()
        
        if not token:
            return jsonify({'code': 401, 'message': '获取飞书访问令牌失败，请检查应用配置'})
        
        # 测试获取多维表格记录
        url = f"{FeishuWorkhourConfig.API_BASE_URL}/open-apis/bitable/v1/apps/{bitable_app_token}/tables/{project_table_id}/records"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        params = {'page_size': 10}
        
        response = requests.get(url, headers=headers, params=params)
        result = response.json()
        
        if result.get('code') == 0:
            records = result.get('data', {}).get('items', [])
            return jsonify({
                'code': 200, 
                'message': '连接成功',
                'project_count': len(records)
            })
        else:
            return jsonify({
                'code': result.get('code', 500),
                'message': f"飞书API错误: {result.get('msg', '未知错误')}"
            })
            
    except Exception as e:
        return jsonify({'code': 500, 'message': f'连接测试失败: {str(e)}'})


@workhour_bp.route('/admin/notification/', methods=['POST'])
@login_required
@admin_required
def admin_send_notification():
    """手动发送填报通知"""
    try:
        feishu_api = get_feishu_api()
        
        # 获取所有需要通知的员工（已激活且非例外员工）
        employees = Employee.query.filter_by(is_active=True, is_exempt=False).all()
        
        sent_count = 0
        exempt_count = 0
        
        # 获取例外员工数量（用于显示）
        total_active = Employee.query.filter_by(is_active=True).count()
        
        for emp in employees:
            try:
                form_url = request.host_url.rstrip('/') + url_for('workhour.index')
                feishu_api.send_workhour_reminder(
                    user_id=emp.feishu_user_id,
                    user_name=emp.name,
                    month=datetime.now().strftime('%Y年%m月'),
                    work_days=get_work_days_in_month(datetime.now().year, datetime.now().month),
                    form_url=form_url
                )
                sent_count += 1
            except Exception as e:
                current_app.logger.warning(f'发送通知失败 {emp.name}: {e}')
        
        # 计算例外员工数量
        exempt_count = total_active - len(employees)
        exempt_msg = f'（已跳过 {exempt_count} 名例外员工）' if exempt_count > 0 else ''
        flash(f'已向 {sent_count} 名员工发送通知{exempt_msg}', 'success')
        
    except Exception as e:
        flash(f'发送通知失败: {str(e)}', 'error')
    
    return redirect(url_for('workhour.admin_status'))
