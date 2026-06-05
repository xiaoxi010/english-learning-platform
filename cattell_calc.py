# cattell_calc.py — 卡特尔 16PF 计分（与小程序逻辑一致）
from __future__ import annotations

from cattell_loader import load_careers, load_dimensions, load_norms, load_scoring, load_secondary

DIM_KEYS = ['A', 'B', 'C', 'E', 'F', 'G', 'H', 'I', 'L', 'M', 'N', 'O', 'Q1', 'Q2', 'Q3', 'Q4']


def _discrete_level(standard_score):
    try:
        r = round(float(standard_score))
    except (TypeError, ValueError):
        r = 5
    u = max(0, min(10, r))
    if u <= 3:
        return '低分'
    if u == 4:
        return '偏低'
    if u == 5:
        return '中等'
    if u in (6, 7):
        return '偏高'
    return '高分'


def _secondary_on_ten(std):
    s = std

    def _f(id_, raw, scale):
        v = float(raw)
        if id_.startswith('X'):
            pass
        elif id_ == 'Y1':
            v = v / 4
        elif id_ == 'Y2':
            v = v / 10
        elif id_ == 'Y3':
            v = v / 18
        elif id_ == 'Y4':
            v = v / 4
        return round(max(1, min(10, v)) * 10) / 10

    formulas = {
        'X1': lambda: (38 + 2 * s['L'] + 3 * s['O'] + 4 * s['Q4'] - 2 * s['C'] - 2 * s['H'] - 2 * s['Q3']) / 10,
        'X2': lambda: (2 * s['A'] + 3 * s['E'] + 4 * s['F'] + 5 * s['H'] - 2 * s['Q2'] - 11) / 10,
        'X3': lambda: (77 + 2 * s['C'] + 2 * s['E'] + 2 * s['F'] + 2 * s['N'] - 4 * s['A'] - 6 * s['I'] - 2 * s['M']) / 10,
        'X4': lambda: (4 * s['E'] + 3 * s['M'] + 4 * s['Q1'] + 4 * s['Q2'] - 3 * s['A'] - 2 * s['G']) / 10,
        'Y1': lambda: s['C'] + s['F'] + (11 - s['O']) + (11 - s['Q4']),
        'Y2': lambda: 2 * s['Q3'] + 2 * s['G'] + 2 * s['C'] + s['E'] + s['N'] + s['Q2'] + s['Q1'],
        'Y3': lambda: (11 - s['A']) * 2 + 2 * s['B'] + s['E'] + (11 - s['F']) * 2 + s['H'] + 2 * s['I'] + s['M'] + (11 - s['N']) + s['Q1'] + 2 * s['Q2'],
        'Y4': lambda: s['B'] + s['G'] + s['Q3'] + (11 - s['F']),
    }
    out = {}
    for fid, fn in formulas.items():
        try:
            raw = fn()
            if raw != raw:
                out[fid] = 5.0
            else:
                out[fid] = _f(fid, raw, None)
        except (KeyError, TypeError):
            out[fid] = 5.0
    return out


def _career_match_single(user_std, career):
    total = 0.0
    for dim in career.get('dimensions') or []:
        code = dim['code']
        user_score = float(user_std.get(code, 5))
        weight = float(dim.get('weight', 0))
        if dim.get('require') == '高':
            total += (user_score / 10) * weight
        else:
            total += ((11 - user_score) / 10) * weight
    prob = round(total, 4)
    level = '高度匹配' if prob >= 0.8 else ('中度匹配' if prob >= 0.6 else '不太匹配')
    return {
        'careerId': career['id'],
        'careerName': career['name'],
        'matchProbability': prob,
        'matchLevel': level,
    }


def _career_rank(user_std, top_n=15):
    rows = [_career_match_single(user_std, c) for c in load_careers()]
    rows.sort(key=lambda x: x['matchProbability'], reverse=True)
    return [
        {
            'id': r['careerId'],
            'name': r['careerName'],
            'percent': min(100, max(0, round(r['matchProbability'] * 100))),
            'level': r['matchLevel'],
        }
        for r in rows[:top_n]
    ]


def _raw_to_standard(raw_scores, norms):
    std = {}
    for dim in DIM_KEYS:
        raw = int(raw_scores.get(dim, 0))
        std[dim] = 5
        for band in norms.get(dim) or []:
            if band['rawMin'] <= raw <= band['rawMax']:
                std[dim] = int(band['standard'])
                break
    return std


def run_cattell_test(answers_abc):
    """
    answers_abc: 长度 187 的列表，每项为 'A'|'B'|'C' 或空串
    """
    scoring = load_scoring()
    norms = load_norms()
    n = 187
    if len(answers_abc) < n:
        answers_abc = list(answers_abc) + [''] * (n - len(answers_abc))
    answers_abc = answers_abc[:n]

    question_scores = [0] * n
    type1 = {(r['questionId'], r['option']) for r in scoring.get('scoreType1', [])}
    type2 = {r['questionId']: r['option'] for r in scoring.get('scoreType2', [])}

    for qi in range(n):
        ans = answers_abc[qi]
        qid = qi + 1
        if ans == 'B' and qid in type2:
            question_scores[qi] = 1
        elif (qid, ans) in type1:
            question_scores[qi] = 1
        elif type2.get(qid) == ans:
            question_scores[qi] = 2

    raw = {k: 0 for k in DIM_KEYS}
    for dim, qids in (scoring.get('dimensionQuestions') or {}).items():
        for qid in qids:
            raw[dim] += question_scores[qid - 1]

    std = _raw_to_standard(raw, norms)
    dimensions_meta = {d['id']: d for d in load_dimensions()}

    dimension_analysis = []
    for dim_id in DIM_KEYS:
        meta = dimensions_meta.get(dim_id, {'id': dim_id, 'name': dim_id})
        standard_score = std[dim_id]
        level = _discrete_level(standard_score)
        low_c = (meta.get('suitableCareers') or {}).get('low') or []
        high_c = (meta.get('suitableCareers') or {}).get('high') or []
        if level == '低分':
            desc = meta.get('lowDesc', '')
            careers = low_c
        elif level == '偏低':
            desc = f'标准分 {standard_score}（略偏低，接近典型低分一侧）。{meta.get("lowDesc", "")}'
            careers = low_c
        elif level == '中等':
            desc = '处于中等水平，兼具高低分特征的平衡表现'
            careers = (low_c + high_c)[:5]
        elif level == '偏高':
            desc = f'标准分 {standard_score}（略偏高，接近典型高分一侧）。{meta.get("highDesc", "")}'
            careers = high_c
        else:
            desc = meta.get('highDesc', '')
            careers = high_c
        dimension_analysis.append({
            'id': dim_id,
            'name': meta.get('name', dim_id),
            'rawScore': raw[dim_id],
            'standardScore': standard_score,
            'level': level,
            'description': desc,
            'suitableCareers': careers[:8],
        })

    on_ten = _secondary_on_ten(std)
    secondary_factors = []
    for f in load_secondary():
        fid = f['id']
        display = on_ten.get(fid, 5.0)
        level = _discrete_level(display)
        if level == '低分':
            desc = f.get('lowDesc', '')
        elif level == '偏低':
            desc = f'得分约 {display}（略偏低）。{f.get("lowDesc", "")}'
        elif level == '中等':
            desc = f'{display} 分，介于典型低分与高分之间'
        elif level == '偏高':
            desc = f'得分约 {display}（略偏高）。{f.get("highDesc", "")}'
        else:
            desc = f.get('highDesc', '')
        secondary_factors.append({
            'id': fid,
            'name': f.get('name', fid),
            'score': str(display),
            'scoreNum': display,
            'level': level,
            'description': desc,
        })

    career_rank = _career_rank(std)

    return {
        'dimensionRawScores': raw,
        'dimensionStandardScores': std,
        'dimensionAnalysis': dimension_analysis,
        'secondaryFactors': secondary_factors,
        'secondaryScoresOnTen': on_ten,
        'careerRank': career_rank,
        'answers': answers_abc,
        'questionScores': question_scores,
    }
