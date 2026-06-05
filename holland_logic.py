# holland_logic.py — 霍兰德报告组装
from datetime import datetime

from holland_calc import (
    DIM_META,
    MAX_SCORE,
    build_bar_rows,
    build_holland_dim_cards_top_three,
    calculate_holland_scores,
    holland_top_three_riasec_sorted_from_scores,
    holland_triple_code_from_scores,
    pick_holland_triple_careers,
)
from holland_loader import load_dimensions, load_questions, load_triple_careers


def parse_answers(form, total):
    answers = []
    for i in range(total):
        v = (form.get(f'ans_{i}') or form.get(f'ans[{i}]') or '').strip().upper()
        if v not in ('A', 'B'):
            answers.append('')
        else:
            answers.append(v)
    return answers


def build_holland_report(user_name, answers):
    questions = load_questions()
    n = len(questions)
    if not n:
        raise ValueError('霍兰德题库未加载，请将数据文件放到 data/ 目录')

    if len(answers) < n:
        answers = list(answers) + [''] * (n - len(answers))
    answers = answers[:n]

    for i, a in enumerate(answers):
        if a not in ('A', 'B'):
            raise ValueError(f'请完成第 {i + 1} 题')

    scores = calculate_holland_scores(answers)
    dimensions = load_dimensions()
    triple_map = load_triple_careers()
    triple_code = holland_triple_code_from_scores(scores)
    top_three_sorted = holland_top_three_riasec_sorted_from_scores(scores)
    triple_block = pick_holland_triple_careers(triple_map, triple_code) or {}
    careers = triple_block.get('careers') or []
    match_rows = [
        {'name': c.get('name', ''), 'rate': c.get('matchRate', c.get('match_rate', 0))}
        for c in careers[:3]
    ]
    dim_cards = build_holland_dim_cards_top_three(scores, dimensions)

    if triple_block:
        match_summary = (
            f'职业匹配算法代码「{triple_code}」（{triple_block.get("name", "")}）；'
            f'得分最高三维为「{top_three_sorted}」。'
            f'下列职业与算法组合关联度较高，可作探索参考（结果仅供生涯启发，非职业鉴定）。'
        )
    else:
        match_summary = (
            f'职业匹配代码「{triple_code}」暂无库条目；得分最高三维为「{top_three_sorted}」。'
            f'下列方向可作一般探索参考（结果仅供生涯启发）。'
        )

    return {
        'user_name': user_name,
        'scores': scores,
        'bar_rows': build_bar_rows(scores),
        'triple_code': triple_code,
        'triple_code_display': triple_code,
        'triple_name': triple_block.get('name', ''),
        'top_three_sorted': top_three_sorted,
        'dim_cards': dim_cards,
        'match_rows': match_rows,
        'match_summary': match_summary,
        'max_score': MAX_SCORE,
        'question_count': n,
        'calculate_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'data_ready': True,
        'radar_labels': [d['name'] for d in DIM_META],
        'radar_values': [scores.get(k, 0) for k in ['R', 'I', 'A', 'S', 'E', 'C']],
    }
