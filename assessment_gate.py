# assessment_gate.py - 吉致核心测评访问密码（学科 / 数字天赋 / 人生道路）
from flask import render_template, session, url_for

CORE_ASSESSMENT_PASSWORD = '985211'
SESSION_KEY = 'core_assessment_unlocked'


def is_core_assessment_unlocked():
    return session.get(SESSION_KEY) is True


def try_unlock_core_assessment(password):
    if (password or '').strip() == CORE_ASSESSMENT_PASSWORD:
        session[SESSION_KEY] = True
        return True
    return False


def handle_gate_unlock_post(request, flash):
    """处理密码表单 POST；验证成功返回 True，失败 flash 并返回 False。"""
    if request.method != 'POST' or request.form.get('_assessment_gate') != '1':
        return None
    if try_unlock_core_assessment(request.form.get('access_password')):
        return True
    flash('密码错误，请重试', 'error')
    return False


def require_core_assessment_unlock(gate_title, unlock_endpoint, back_url='index'):
    """未解锁时返回密码页 Response，已解锁返回 None。"""
    if is_core_assessment_unlocked():
        return None
    return render_template(
        'partials/assessment_password_gate.html',
        gate_title=gate_title,
        unlock_url=url_for(unlock_endpoint),
        back_url=url_for(back_url),
        show_sidebar=True,
        active_nav='assessment',
    )
