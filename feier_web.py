# feier_web.py — 菲尔人格测评（Phil McGraw 十项）
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from feier_loader import data_ready, load_meta, load_questions
from feier_logic import build_feier_report, parse_answers
from settings_web import get_user_settings

feier_bp = Blueprint('feier', __name__)


def _welcome():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@feier_bp.route('/assessment/feier')
def start():
    meta = load_meta() if data_ready() else {}
    return render_template(
        'feier/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='菲尔人格测评',
        page_subtitle='10 题经典版',
        welcome_name=_welcome(),
        data_ready=data_ready(),
        meta=meta,
    )


@feier_bp.route('/assessment/feier/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        name = (request.form.get('user_name') or '').strip()
        if not name:
            flash('请填写姓名', 'error')
            return redirect(url_for('feier.start'))
        session['feier_user_name'] = name
        return redirect(url_for('feier.quiz'))

    name = session.get('feier_user_name', '').strip()
    if not name:
        return redirect(url_for('feier.start'))

    questions = load_questions()
    if len(questions) != 10:
        flash('菲尔人格题库未加载', 'error')
        return redirect(url_for('feier.start'))

    return render_template(
        'feier/quiz.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='菲尔人格测评',
        page_subtitle=name,
        user_name=name,
        questions=questions,
        total=len(questions),
    )


@feier_bp.route('/assessment/feier/report', methods=['POST'])
def report():
    name = session.get('feier_user_name', '').strip()
    if not name:
        name = (request.form.get('user_name') or '').strip()
    if not name:
        flash('请先填写姓名并开始测评', 'error')
        return redirect(url_for('feier.start'))

    answers = parse_answers(request.form)

    try:
        report_data = build_feier_report(name, answers)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('feier.quiz'))
    except Exception:
        flash('报告生成失败，请稍后重试', 'error')
        return redirect(url_for('feier.quiz'))

    return render_template(
        'feier/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='菲尔人格测评报告',
        page_subtitle=name,
        report=report_data,
    )
