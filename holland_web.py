# holland_web.py — 霍兰德职业兴趣测评
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from holland_loader import data_ready, load_questions
from holland_logic import build_holland_report, parse_answers
from settings_web import get_user_settings

holland_bp = Blueprint('holland', __name__)


def _welcome():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@holland_bp.route('/assessment/holland')
def start():
    return render_template(
        'holland/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='霍兰德职业兴趣测评',
        page_subtitle='RIASEC 六维 · 职业兴趣匹配',
        welcome_name=_welcome(),
        data_ready=data_ready(),
    )


@holland_bp.route('/assessment/holland/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        name = (request.form.get('user_name') or request.form.get('name') or '').strip()
        if not name:
            flash('请填写姓名', 'error')
            return redirect(url_for('holland.start'))
        session['holland_user_name'] = name
        return redirect(url_for('holland.quiz'))

    name = session.get('holland_user_name', '').strip()
    if not name:
        return redirect(url_for('holland.start'))

    questions = load_questions()
    if not questions:
        flash('霍兰德题库未加载', 'error')
        return redirect(url_for('holland.start'))

    return render_template(
        'holland/quiz.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='霍兰德职业兴趣测评',
        page_subtitle=name,
        user_name=name,
        questions=questions,
        total=len(questions),
    )


@holland_bp.route('/assessment/holland/report', methods=['POST'])
def report():
    name = session.get('holland_user_name', '').strip()
    if not name:
        name = (request.form.get('user_name') or '').strip()
    if not name:
        flash('请先填写姓名并开始测评', 'error')
        return redirect(url_for('holland.start'))

    questions = load_questions()
    n = len(questions)
    answers = parse_answers(request.form, n)

    try:
        report_data = build_holland_report(name, answers)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('holland.quiz'))

    return render_template(
        'holland/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='霍兰德职业兴趣测评报告',
        page_subtitle=name,
        report=report_data,
    )
