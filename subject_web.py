# subject_web.py - 学科能力测评
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from subject_logic import build_subject_report
from subject_loader import ability_ready
from digital_talent_logic import parse_birth_date, parse_birth_selectors, format_birth_display
from settings_web import get_user_settings
from assessment_gate import (
    handle_gate_unlock_post,
    is_core_assessment_unlocked,
    require_core_assessment_unlock,
)

subject_bp = Blueprint('subject', __name__)


def _years():
    return list(range(datetime.now().year, 1999, -1))


def _welcome():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@subject_bp.route('/assessment/subject', methods=['GET', 'POST'])
def start():
    if handle_gate_unlock_post(request, flash) is True:
        return redirect(url_for('subject.start'))
    gate = require_core_assessment_unlock('学科能力测评', 'subject.start')
    if gate:
        return gate
    return render_template(
        'subject/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='学科能力测评',
        page_subtitle='学科优劣分析 · 看见天赋与短板',
        welcome_name=_welcome(),
        years=_years(),
        months=list(range(1, 13)),
        days=list(range(1, 32)),
        data_ready=ability_ready(),
    )


@subject_bp.route('/assessment/subject/report', methods=['POST'])
def report():
    if not is_core_assessment_unlocked():
        flash('请先输入访问密码', 'error')
        return redirect(url_for('subject.start'))
    name = (request.form.get('name') or '').strip()
    gender = request.form.get('gender', '')
    if gender == '请选择':
        gender = ''
    birth = request.form.get('birth_date', '')
    if not birth:
        p = parse_birth_selectors(
            request.form.get('birth_year'),
            request.form.get('birth_month'),
            request.form.get('birth_day'),
        )
        if p:
            birth = format_birth_display(*p)
    parsed = parse_birth_date(birth)
    if not name:
        flash('请输入姓名', 'error')
        return redirect(url_for('subject.start'))
    if not parsed:
        flash('请选择2000年1月1日及以后的出生日期', 'error')
        return redirect(url_for('subject.start'))
    if parsed[0] < 2000:
        flash('本测评仅支持2000年1月1日及以后的出生日期', 'error')
        return redirect(url_for('subject.start'))

    try:
        report_data = build_subject_report(
            name, gender, *parsed,
            ethnicity=request.form.get('ethnicity', '').strip(),
        )
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('subject.start'))

    return render_template(
        'subject/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='学科能力测评报告',
        page_subtitle=name,
        report=report_data,
        data_ready=report_data.get('data_ready', False),
    )
