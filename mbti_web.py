# mbti_web.py — 趣味测评 MBTI 48 题精确版
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mbti_loader import data_ready, load_likert, load_questions
from mbti_logic import build_mbti_report, parse_answers
from settings_web import get_user_settings

mbti_bp = Blueprint('mbti', __name__)


def _welcome():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@mbti_bp.route('/assessment/mbti')
def start():
    return render_template(
        'mbti/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='MBTI 趣味测评',
        page_subtitle='48 题精确版',
        welcome_name=_welcome(),
        data_ready=data_ready(),
    )


@mbti_bp.route('/assessment/mbti/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        name = (request.form.get('user_name') or '').strip()
        if not name:
            flash('请填写姓名', 'error')
            return redirect(url_for('mbti.start'))
        session['mbti_user_name'] = name
        return redirect(url_for('mbti.quiz'))

    name = session.get('mbti_user_name', '').strip()
    if not name:
        return redirect(url_for('mbti.start'))

    questions = load_questions()
    if len(questions) != 48:
        flash('MBTI 题库未加载', 'error')
        return redirect(url_for('mbti.start'))

    return render_template(
        'mbti/quiz.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='MBTI 趣味测评',
        page_subtitle=name,
        user_name=name,
        questions=questions,
        total=len(questions),
        likert_options=load_likert(),
    )


@mbti_bp.route('/assessment/mbti/report', methods=['POST'])
def report():
    name = session.get('mbti_user_name', '').strip()
    if not name:
        name = (request.form.get('user_name') or '').strip()
    if not name:
        flash('请先填写姓名并开始测评', 'error')
        return redirect(url_for('mbti.start'))

    n = len(load_questions())
    answers = parse_answers(request.form, n)

    try:
        report_data = build_mbti_report(name, answers)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('mbti.quiz'))
    except Exception:
        flash('报告生成失败，请稍后重试', 'error')
        return redirect(url_for('mbti.quiz'))

    return render_template(
        'mbti/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='MBTI 测评报告',
        page_subtitle=name,
        report=report_data,
    )
