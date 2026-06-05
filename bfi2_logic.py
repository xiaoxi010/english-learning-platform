# bfi2_logic.py
from datetime import datetime

from bfi2_calc import run_bfi2_test
from bfi2_loader import load_meta, load_questions

OPTIONS = ('1', '2', '3', '4', '5')


def parse_answers(form, total):
    answers = []
    for i in range(total):
        v = (form.get(f'ans_{i}') or '').strip()
        if v not in OPTIONS:
            answers.append('')
        else:
            answers.append(v)
    return answers


def build_bfi2_report(user_name, answers, finished_at_ms=None):
    questions = load_questions()
    n = len(questions)
    if n != 60:
        raise ValueError('BFI-2 题库未加载完整（需 60 题）')

    if len(answers) < n:
        answers = list(answers) + [''] * (n - len(answers))
    answers = answers[:n]

    for i, a in enumerate(answers):
        if a not in OPTIONS:
            raise ValueError(f'请完成第 {i + 1} 题')

    now = finished_at_ms or int(datetime.now().timestamp() * 1000)
    finished_dt = datetime.fromtimestamp(now / 1000)
    meta = load_meta()

    result = run_bfi2_test(answers)
    top = sorted(result['dimensionReports'], key=lambda d: d['score'], reverse=True)[:2]
    summary_bits = [f"{d['name']}{d['label']}" for d in top]
    summary = f"{user_name} · " + ' · '.join(summary_bits) if summary_bits else f'{user_name} · 大五人格 BFI-2'

    return {
        'user_name': user_name,
        'summary': summary,
        'calculate_time': finished_dt.strftime('%Y-%m-%d %H:%M'),
        'report_id': f"BFI-{finished_dt.strftime('%Y%m%d')}-{now % 100000:05d}",
        'meta': meta,
        'result': result,
        'data_ready': True,
    }
