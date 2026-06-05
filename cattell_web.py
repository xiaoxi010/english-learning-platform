# cattell_web.py — 卡特尔 16PF 人格因素测评
import time

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from cattell_loader import data_ready, load_questions
from cattell_logic import build_cattell_report, parse_answers
from settings_web import get_user_settings

cattell_bp = Blueprint('cattell', __name__)


def _welcome():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@cattell_bp.route('/assessment/cattell')
def start():
    return render_template(
        'cattell/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='卡特尔 16PF 人格因素测评',
        page_subtitle='187 题 · 16 维人格与职业匹配',
        welcome_name=_welcome(),
        data_ready=data_ready(),
    )


@cattell_bp.route('/assessment/cattell/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        name = (request.form.get('user_name') or '').strip()
        if not name:
            flash('请填写姓名', 'error')
            return redirect(url_for('cattell.start'))
        session['cattell_user_name'] = name
        session['cattell_started_at'] = int(time.time() * 1000)
        return redirect(url_for('cattell.quiz'))

    name = session.get('cattell_user_name', '').strip()
    if not name:
        return redirect(url_for('cattell.start'))
    if not session.get('cattell_started_at'):
        session['cattell_started_at'] = int(time.time() * 1000)

    questions = load_questions()
    if len(questions) != 187:
        flash('卡特尔题库未加载', 'error')
        return redirect(url_for('cattell.start'))

    return render_template(
        'cattell/quiz.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='卡特尔 16PF 人格因素测评',
        page_subtitle=name,
        user_name=name,
        questions=questions,
        total=len(questions),
    )


@cattell_bp.route('/assessment/cattell/report', methods=['POST'])
def report():
    name = session.get('cattell_user_name', '').strip()
    if not name:
        name = (request.form.get('user_name') or '').strip()
    if not name:
        flash('请先填写姓名并开始测评', 'error')
        return redirect(url_for('cattell.start'))

    n = len(load_questions())
    answers = parse_answers(request.form, n)

    try:
        report_data = build_cattell_report(
            name,
            answers,
            finished_at_ms=int(time.time() * 1000),
        )
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('cattell.quiz'))
    except Exception:
        flash('报告生成失败，请稍后重试', 'error')
        return redirect(url_for('cattell.quiz'))

    return render_template(
        'cattell/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='卡特尔 16PF 测评报告',
        page_subtitle=name,
        report=report_data,
    )
