# mbti_calc.py — 48 题 MBTI 趣味测评计分
from __future__ import annotations

from mbti_loader import load_questions, load_types

POLARITY = [
    ('EI', 'E', 'I'),
    ('NS', 'N', 'S'),
    ('FT', 'F', 'T'),
    ('JP', 'J', 'P'),
]

VALID = frozenset(range(-2, 3))


def calculate_mbti(questions, answers):
    """answers: 长度 48，每项为 -2..2 的整数"""
    if len(questions) != 48 or len(answers) != 48:
        raise ValueError('题目和答案数量必须为 48 道')

    stats = {k: {'raw': 0, 'count': 0} for k, _, _ in POLARITY}

    for q, ans in zip(questions, answers):
        score = int(ans)
        if q.get('reverse'):
            score = -score
        dim = q['dimension']
        stats[dim]['raw'] += score
        stats[dim]['count'] += 1

    dimensions = {}
    full_type = ''

    for key, positive, negative in POLARITY:
        raw = stats[key]['raw']
        count = stats[key]['count']
        min_raw = -2 * count
        max_raw = 2 * count
        pct = ((raw - min_raw) / (max_raw - min_raw)) * 100 if max_raw > min_raw else 50.0
        polarity = positive if pct >= 50 else negative
        dimensions[key] = {
            'rawScore': raw,
            'percentage': round(pct, 1),
            'percentageText': f'{pct:.1f}%',
            'polarity': polarity,
            'tendency': f'偏向{positive}' if pct >= 50 else f'偏向{negative}',
        }
        full_type += polarity

    legacy = _legacy_scores(dimensions)
    return {
        'dimensions': dimensions,
        'fullType': full_type,
        'legacyScores': legacy,
    }


def _legacy_scores(dimensions):
    p_ei = dimensions['EI']['percentage']
    p_ns = dimensions['NS']['percentage']
    p_ft = dimensions['FT']['percentage']
    p_jp = dimensions['JP']['percentage']
    return {
        'E': round(p_ei, 1),
        'I': round(100 - p_ei, 1),
        'N': round(p_ns, 1),
        'S': round(100 - p_ns, 1),
        'F': round(p_ft, 1),
        'T': round(100 - p_ft, 1),
        'J': round(p_jp, 1),
        'P': round(100 - p_jp, 1),
    }


def build_type_report(full_type, calc_result):
    meta = load_types()
    t = full_type.upper()
    dim_details = {}
    for letter in ('E', 'I', 'S', 'N', 'T', 'F', 'J', 'P'):
        arr = meta.get(letter) or []
        if arr:
            dim_details[letter] = {
                'title': arr[0],
                'details': arr[1:],
            }

    return {
        'type': t,
        'total_word': meta.get('total_word', {}).get(t, ''),
        'another_name': meta.get('another_name', {}).get(t, ''),
        'point_word': meta.get('point_word', {}).get(t, []) or [],
        'personal_feature': meta.get('personal_feature', {}).get(t, ''),
        'personal_blind_spot': meta.get('personal_blind_spot', {}).get(t, ''),
        'job_advantage': meta.get('job_advantage', {}).get(t, ''),
        'job_disadvantage': meta.get('job_disadvantage', {}).get(t, ''),
        'post_characteristic': meta.get('post_characteristic', {}).get(t, ''),
        'fit_career': meta.get('fit_career', {}).get(t, ''),
        'fit_environment': meta.get('fit_environment', {}).get(t, ''),
        'development_suggestion': meta.get('development_suggestion', {}).get(t, ''),
        'dimensionDetails': dim_details,
        'dimensions': calc_result['dimensions'],
        'legacyScores': calc_result['legacyScores'],
    }


def run_mbti_test(answers_int):
    questions = load_questions()
    calc = calculate_mbti(questions, answers_int)
    report = build_type_report(calc['fullType'], calc)
    return {**calc, 'report': report}
