# lifeway_web.py - 人生道路解读
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from lifeway_logic import build_lifeway_report
from lifeway_loader import lifeway_ready
from digital_talent_logic import parse_birth_date, parse_birth_selectors, format_birth_display
from settings_web import get_user_settings
from assessment_gate import (
    handle_gate_unlock_post,
    is_core_assessment_unlocked,
    require_core_assessment_unlock,
)

lifeway_bp = Blueprint('lifeway', __name__)


def _year_options():
    return list(range(datetime.now().year, 1899, -1))


def _welcome_name():
    logged_in = session.get('user')
    if logged_in:
        settings = get_user_settings(logged_in['id'])
        return settings.get('account_name') or settings.get('user_name') or '朋友'
    return '朋友'


@lifeway_bp.route('/assessment/lifeway', methods=['GET', 'POST'])
def start():
    if handle_gate_unlock_post(request, flash) is True:
        return redirect(url_for('lifeway.start'))
    gate = require_core_assessment_unlock('人生道路解读', 'lifeway.start')
    if gate:
        return gate
    return render_template(
        'lifeway/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='人生道路解读',
        page_subtitle='毕达哥拉斯数字生命学测评',
        welcome_name=_welcome_name(),
        years=_year_options(),
        months=list(range(1, 13)),
        days=list(range(1, 32)),
        data_ready=lifeway_ready(),
    )


@lifeway_bp.route('/assessment/lifeway/report', methods=['POST'])
def report():
    if not is_core_assessment_unlocked():
        flash('请先输入访问密码', 'error')
        return redirect(url_for('lifeway.start'))
    user_name = (request.form.get('user_name') or '').strip()
    user_name_pinyin = (request.form.get('user_name_pinyin') or '').strip().lower()
    birth = request.form.get('birth_date', '')
    if not birth:
        parsed_sel = parse_birth_selectors(
            request.form.get('birth_year'),
            request.form.get('birth_month'),
            request.form.get('birth_day'),
        )
        if parsed_sel:
            birth = format_birth_display(*parsed_sel)

    parsed = parse_birth_date(birth)
    if not parsed:
        flash('请选择有效的生日', 'error')
        return redirect(url_for('lifeway.start'))
    if not user_name_pinyin:
        flash('请填写姓名拼音（小写）', 'error')
        return redirect(url_for('lifeway.start'))

    try:
        report_data = build_lifeway_report(user_name, user_name_pinyin, *parsed)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('lifeway.start'))

    return render_template(
        'lifeway/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='人生道路解读报告',
        page_subtitle=report_data['user_name'],
        report=report_data,
        data_ready=report_data.get('data_ready', False),
    )
