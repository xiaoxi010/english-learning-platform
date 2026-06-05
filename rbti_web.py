# rbti_web.py — RBTI 年度抽象人格测评
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from rbti_loader import data_ready, load_meta, load_questions
from rbti_logic import build_rbti_report, parse_answers
from settings_web import get_user_settings

rbti_bp = Blueprint('rbti', __name__)


def _welcome():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@rbti_bp.route('/assessment/rbti')
def start():
    return render_template(
        'rbti/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='RBTI 抽象人格测评',
        page_subtitle='31 题趣味版',
        welcome_name=_welcome(),
        data_ready=data_ready(),
        meta=load_meta() if data_ready() else {},
    )


@rbti_bp.route('/assessment/rbti/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        name = (request.form.get('user_name') or '').strip()
        if not name:
            flash('请填写姓名', 'error')
            return redirect(url_for('rbti.start'))
        session['rbti_user_name'] = name
        return redirect(url_for('rbti.quiz'))

    name = session.get('rbti_user_name', '').strip()
    if not name:
        return redirect(url_for('rbti.start'))

    questions = load_questions()
    if len(questions) != 31:
        flash('RBTI 题库未加载', 'error')
        return redirect(url_for('rbti.start'))

    return render_template(
        'rbti/quiz.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='RBTI 抽象人格测评',
        page_subtitle=name,
        user_name=name,
        questions=questions,
        total=len(questions),
    )


@rbti_bp.route('/assessment/rbti/report', methods=['POST'])
def report():
    name = session.get('rbti_user_name', '').strip()
    if not name:
        name = (request.form.get('user_name') or '').strip()
    if not name:
        flash('请先填写姓名并开始测评', 'error')
        return redirect(url_for('rbti.start'))

    n = len(load_questions())
    answers = parse_answers(request.form, n)

    try:
        report_data = build_rbti_report(name, answers)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('rbti.quiz'))
    except Exception:
        flash('报告生成失败，请稍后重试', 'error')
        return redirect(url_for('rbti.quiz'))

    return render_template(
        'rbti/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='RBTI 测评报告',
        page_subtitle=name,
        report=report_data,
    )
