# feier_logic.py
from datetime import datetime

from feier_calc import compute_feier_total_score, get_feier_result_meta
from feier_loader import load_meta, load_questions, load_score_table

QUESTION_COUNT = 10


def parse_answers(form, total=None):
    questions = load_questions()
    table = load_score_table()
    n = total if total is not None else len(questions)
    answers = []
    for i in range(n):
        v = (form.get(f'ans_{i}') or '').strip().upper()
        valid = set(table[i].keys()) if i < len(table) else set()
        if v not in valid:
            answers.append(None)
        else:
            answers.append(v)
    return answers


def build_feier_report(user_name, answers):
    questions = load_questions()
    table = load_score_table()
    if len(questions) != QUESTION_COUNT or len(table) != QUESTION_COUNT:
        raise ValueError('菲尔人格题库未加载完整（需 10 题）')

    if len(answers) < QUESTION_COUNT:
        answers = list(answers) + [None] * (QUESTION_COUNT - len(answers))
    answers = answers[:QUESTION_COUNT]

    for i, a in enumerate(answers):
        if a is None:
            raise ValueError(f'请完成第 {i + 1} 题')
        if a not in table[i]:
            raise ValueError(f'第 {i + 1} 题选项无效')

    total_score = compute_feier_total_score(answers)
    meta = get_feier_result_meta(total_score)
    info = load_meta()

    now = datetime.now()
    return {
        'user_name': user_name,
        'summary': f'{user_name} · {meta.get("title", "")} · {total_score} 分',
        'calculate_time': now.strftime('%Y-%m-%d %H:%M'),
        'report_id': f'FEI-{now.strftime("%Y%m%d")}-{int(now.timestamp()) % 100000:05d}',
        'meta': info,
        'answers': answers,
        'total_score': total_score,
        'result_key': meta.get('key', ''),
        'result_title': meta.get('title', ''),
        'subtitle': meta.get('subtitle', ''),
        'analysis': meta.get('analysis', ''),
        'career_hint': meta.get('careerHint', ''),
        'result': meta,
        'data_ready': True,
    }
