# digital_talent_web.py - 数字天赋解读
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from digital_talent_logic import build_report, parse_birth_date, parse_birth_selectors, format_birth_display
from personality_loader import personality_ready
from assessment_gate import (
    handle_gate_unlock_post,
    is_core_assessment_unlocked,
    require_core_assessment_unlock,
)
from settings_web import get_user_settings

digital_talent_bp = Blueprint('digital_talent', __name__)


def _year_options():
    end = datetime.now().year
    return list(range(end, 1899, -1))


@digital_talent_bp.route('/assessment/digital-talent', methods=['GET', 'POST'])
def start():
    if handle_gate_unlock_post(request, flash) is True:
        return redirect(url_for('digital_talent.start'))
    gate = require_core_assessment_unlock('数字天赋解读', 'digital_talent.start')
    if gate:
        return gate
    welcome_name = '朋友'
    logged_in = session.get('user')
    if logged_in:
        settings = get_user_settings(logged_in['id'])
        welcome_name = (
            settings.get('account_name')
            or settings.get('user_name')
            or '朋友'
        )
    return render_template(
        'digital_talent/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='数字天赋解读',
        page_subtitle='根据出生日期解读天赋密码',
        welcome_name=welcome_name,
        years=_year_options(),
        months=list(range(1, 13)),
        days=list(range(1, 32)),
        data_ready=personality_ready(),
    )


@digital_talent_bp.route('/assessment/digital-talent/report', methods=['GET', 'POST'])
def report():
    if not is_core_assessment_unlocked():
        flash('请先输入访问密码', 'error')
        return redirect(url_for('digital_talent.start'))
    birth = ''
    if request.method == 'POST':
        birth = request.form.get('birth_date', '')
        if not birth:
            y = request.form.get('birth_year')
            m = request.form.get('birth_month')
            d = request.form.get('birth_day')
            parsed_sel = parse_birth_selectors(y, m, d)
            if parsed_sel:
                birth = format_birth_display(*parsed_sel)
    else:
        birth = request.args.get('birth_date', '')

    parsed = parse_birth_date(birth)
    if not parsed:
        flash('请选择有效的出生日期', 'error')
        return redirect(url_for('digital_talent.start'))

    report_data = build_report(*parsed)
    return render_template(
        'digital_talent/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='数字天赋解读报告',
        page_subtitle=report_data['birth_display'],
        report=report_data,
        birth_date=birth,
        data_ready=report_data.get('data_ready', False),
    )
