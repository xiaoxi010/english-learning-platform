# cattell_logic.py
from datetime import datetime

from cattell_calc import run_cattell_test
from cattell_loader import load_meta, load_questions

OPTIONS = ('A', 'B', 'C')


def parse_answers(form, total):
    answers = []
    for i in range(total):
        v = (form.get(f'ans_{i}') or '').strip().upper()
        if v not in OPTIONS:
            answers.append('')
        else:
            answers.append(v)
    return answers


def build_cattell_report(user_name, answers, finished_at_ms=None):
    questions = load_questions()
    n = len(questions)
    if n != 187:
        raise ValueError('卡特尔题库未加载完整（需 187 题）')

    if len(answers) < n:
        answers = list(answers) + [''] * (n - len(answers))
    answers = answers[:n]

    for i, a in enumerate(answers):
        if a not in OPTIONS:
            raise ValueError(f'请完成第 {i + 1} 题')

    now = finished_at_ms or int(datetime.now().timestamp() * 1000)
    finished_dt = datetime.fromtimestamp(now / 1000)
    meta = load_meta()

    result = run_cattell_test(answers)
    if not result:
        raise ValueError('计分失败')

    top_dims = sorted(
        result['dimensionAnalysis'],
        key=lambda d: d['standardScore'],
        reverse=True,
    )[:3]
    summary_bits = [f"{d['name']}{d['standardScore']}" for d in top_dims]
    summary = f"{user_name} · " + ' · '.join(summary_bits) if summary_bits else f'{user_name} · 卡特尔16PF'

    return {
        'user_name': user_name,
        'summary': summary,
        'calculate_time': finished_dt.strftime('%Y-%m-%d %H:%M'),
        'report_id': f"CAT-{finished_dt.strftime('%Y%m%d')}-{now % 100000:05d}",
        'meta': meta,
        'result': result,
        'data_ready': True,
    }
