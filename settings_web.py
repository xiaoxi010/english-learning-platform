# settings_web.py - 用户设置（每用户独立 SQLite 数据库）
from functools import wraps

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

from user_settings_db import (
    ensure_user_settings,
    get_user_settings,
    update_user_settings,
    DEFAULT_CREDITS,
)

settings_bp = Blueprint('settings', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_all_settings():
    """获取当前登录用户设置（供考试等模块使用）"""
    user = session.get('user')
    if user:
        return get_user_settings(user['id'])
    return {
        'account_name': '未设置',
        'account_email': '',
        'student_id': '',
        'credits': DEFAULT_CREDITS,
        'user_name': '未设置',
    }


@settings_bp.route('/settings')
@login_required
def settings_page():
    settings = get_all_settings()
    return render_template(
        'settings.html',
        account_name=settings['account_name'],
        account_email=settings['account_email'],
        student_id=settings['student_id'],
        credits=settings['credits'],
        logged_in_user=session.get('user'),
        active_nav='settings',
    )


@settings_bp.route('/api/settings/save', methods=['POST'])
@login_required
def save_settings():
    data = request.get_json() or {}
    account_name = data.get('account_name', data.get('user_name', '')).strip()
    student_id = data.get('student_id', '').strip()

    if not account_name:
        return jsonify({'success': False, 'message': '账户名称不能为空'})

    user_id = session['user']['id']
    if update_user_settings(user_id, account_name, student_id):
        return jsonify({'success': True, 'message': '设置已保存'})
    return jsonify({'success': False, 'message': '保存失败'})


@settings_bp.route('/api/settings/get', methods=['GET'])
@login_required
def get_settings_api():
    settings = get_all_settings()
    return jsonify({'success': True, **settings})
