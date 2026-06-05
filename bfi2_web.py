# bfi2_web.py — 大五人格 BFI-2
import time

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from bfi2_loader import data_ready, load_questions, load_rating_scale
from bfi2_logic import build_bfi2_report, parse_answers
from settings_web import get_user_settings

bfi2_bp = Blueprint('bfi2', __name__)


def _welcome():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@bfi2_bp.route('/assessment/bfi2')
def start():
    return render_template(
        'bfi2/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='大五人格 BFI-2',
        page_subtitle='60 题 · 五维十五面',
        welcome_name=_welcome(),
        data_ready=data_ready(),
    )


@bfi2_bp.route('/assessment/bfi2/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        name = (request.form.get('user_name') or '').strip()
        if not name:
            flash('请填写姓名', 'error')
            return redirect(url_for('bfi2.start'))
        session['bfi2_user_name'] = name
        session['bfi2_started_at'] = int(time.time() * 1000)
        return redirect(url_for('bfi2.quiz'))

    name = session.get('bfi2_user_name', '').strip()
    if not name:
        return redirect(url_for('bfi2.start'))
    if not session.get('bfi2_started_at'):
        session['bfi2_started_at'] = int(time.time() * 1000)

    questions = load_questions()
    if len(questions) != 60:
        flash('BFI-2 题库未加载', 'error')
        return redirect(url_for('bfi2.start'))

    scale = load_rating_scale()
    scale_options = [
        {'value': k, 'label': f'{k}. {scale.get(k, "")}'}
        for k in ('1', '2', '3', '4', '5')
    ]

    return render_template(
        'bfi2/quiz.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='大五人格 BFI-2',
        page_subtitle=name,
        user_name=name,
        questions=questions,
        total=len(questions),
        scale_options=scale_options,
    )


@bfi2_bp.route('/assessment/bfi2/report', methods=['POST'])
def report():
    name = session.get('bfi2_user_name', '').strip()
    if not name:
        name = (request.form.get('user_name') or '').strip()
    if not name:
        flash('请先填写姓名并开始测评', 'error')
        return redirect(url_for('bfi2.start'))

    n = len(load_questions())
    answers = parse_answers(request.form, n)

    try:
        report_data = build_bfi2_report(
            name,
            answers,
            finished_at_ms=int(time.time() * 1000),
        )
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('bfi2.quiz'))
    except Exception:
        flash('报告生成失败，请稍后重试', 'error')
        return redirect(url_for('bfi2.quiz'))

    return render_template(
        'bfi2/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='大五人格 BFI-2 报告',
        page_subtitle=name,
        report=report_data,
    )
