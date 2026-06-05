# constellation_web.py — 星血趣味测评（星座 × 血型）
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from constellation_loader import data_ready
from constellation_logic import BLOOD_TYPES, build_constellation_report, normalize_blood_type
from digital_talent_logic import parse_birth_date, parse_birth_selectors, format_birth_display
from settings_web import get_user_settings

constellation_bp = Blueprint('constellation', __name__)


def _year_options():
    return list(range(datetime.now().year, 1900, -1))


def _welcome_name():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@constellation_bp.route('/assessment/constellation')
def start():
    return render_template(
        'constellation/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='星血趣味测评',
        page_subtitle='星座 × 血型',
        welcome_name=_welcome_name(),
        years=_year_options(),
        months=list(range(1, 13)),
        days=list(range(1, 32)),
        blood_types=list(BLOOD_TYPES),
        data_ready=data_ready(),
    )


@constellation_bp.route('/assessment/constellation/report', methods=['POST'])
def report():
    user_name = (request.form.get('user_name') or '').strip()
    blood_raw = request.form.get('blood_type') or ''
    blood = normalize_blood_type(blood_raw)

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
        return redirect(url_for('constellation.start'))
    if not blood:
        flash('请选择血型', 'error')
        return redirect(url_for('constellation.start'))

    try:
        report_data = build_constellation_report(user_name, *parsed, blood)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('constellation.start'))

    return render_template(
        'constellation/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='星血测评报告',
        page_subtitle=report_data['user_name'],
        report=report_data,
        data_ready=report_data.get('data_ready', False),
    )
