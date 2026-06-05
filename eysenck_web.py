# eysenck_web.py — 艾克森情绪稳定性测评
import time

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from eysenck_loader import data_ready, load_questions
from eysenck_logic import build_eysenck_report, parse_answers
from settings_web import get_user_settings

eysenck_bp = Blueprint('eysenck', __name__)


def _welcome():
    u = session.get('user')
    if u:
        s = get_user_settings(u['id'])
        return s.get('account_name') or s.get('user_name') or '朋友'
    return '朋友'


@eysenck_bp.route('/assessment/eysenck')
def start():
    return render_template(
        'eysenck/start.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='艾克森情绪稳定性测评',
        page_subtitle='210 题 · 七维情绪状态筛查',
        welcome_name=_welcome(),
        data_ready=data_ready(),
    )


@eysenck_bp.route('/assessment/eysenck/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        name = (request.form.get('user_name') or '').strip()
        if not name:
            flash('请填写姓名', 'error')
            return redirect(url_for('eysenck.start'))
        session['eysenck_user_name'] = name
        session['eysenck_started_at'] = int(time.time() * 1000)
        return redirect(url_for('eysenck.quiz'))

    name = session.get('eysenck_user_name', '').strip()
    if not name:
        return redirect(url_for('eysenck.start'))
    if not session.get('eysenck_started_at'):
        session['eysenck_started_at'] = int(time.time() * 1000)

    questions = load_questions()
    if len(questions) != 210:
        flash('艾克森题库未加载', 'error')
        return redirect(url_for('eysenck.start'))

    return render_template(
        'eysenck/quiz.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='艾克森情绪稳定性测评',
        page_subtitle=name,
        user_name=name,
        questions=questions,
        total=len(questions),
        options=['是', '否', '不确定'],
    )


@eysenck_bp.route('/assessment/eysenck/report', methods=['POST'])
def report():
    name = session.get('eysenck_user_name', '').strip()
    if not name:
        name = (request.form.get('user_name') or '').strip()
    if not name:
        flash('请先填写姓名并开始测评', 'error')
        return redirect(url_for('eysenck.start'))

    n = len(load_questions())
    answers = parse_answers(request.form, n)
    started = session.get('eysenck_started_at')

    try:
        report_data = build_eysenck_report(
            name,
            answers,
            started_at_ms=started,
            finished_at_ms=int(time.time() * 1000),
        )
    except (ValueError, TypeError, KeyError) as e:
        flash(str(e) or '报告生成失败', 'error')
        return redirect(url_for('eysenck.quiz'))
    except Exception:
        flash('报告生成失败，请稍后重试', 'error')
        return redirect(url_for('eysenck.quiz'))

    return render_template(
        'eysenck/report.html',
        show_sidebar=True,
        active_nav='assessment',
        page_title='艾克森情绪稳定性测评报告',
        page_subtitle=name,
        report=report_data,
    )
