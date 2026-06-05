# mbti_logic.py
from datetime import datetime

from mbti_calc import run_mbti_test
from mbti_loader import load_meta, load_questions

VALID_VALUES = frozenset({'-2', '-1', '0', '1', '2'})


def parse_answers(form, total):
    answers = []
    for i in range(total):
        v = (form.get(f'ans_{i}') or '').strip()
        if v not in VALID_VALUES:
            answers.append(None)
        else:
            answers.append(int(v))
    return answers


def build_mbti_report(user_name, answers):
    questions = load_questions()
    n = len(questions)
    if n != 48:
        raise ValueError('MBTI 题库未加载完整（需 48 题）')

    if len(answers) < n:
        answers = list(answers) + [None] * (n - len(answers))
    answers = answers[:n]

    for i, a in enumerate(answers):
        if a is None or a not in range(-2, 3):
            raise ValueError(f'请完成第 {i + 1} 题')

    result = run_mbti_test(answers)
    meta = load_meta()
    rep = result['report']
    another = rep.get('another_name') or ''
    summary = f'{user_name} · {result["fullType"]}'
    if another:
        summary += f' · {another}'

    now = datetime.now()
    return {
        'user_name': user_name,
        'summary': summary,
        'calculate_time': now.strftime('%Y-%m-%d %H:%M'),
        'report_id': f'MBT-{now.strftime("%Y%m%d")}-{int(now.timestamp()) % 100000:05d}',
        'meta': meta,
        'full_type': result['fullType'],
        'report': rep,
        'data_ready': True,
    }
