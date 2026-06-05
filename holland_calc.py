# holland_calc.py — RIASEC 计分与报告结构（对齐 hollandCalc.js）
from holland_triple_algorithm import RIASEC, get_unique_holland_code, normalize_scores

MAX_SCORE = 15

DIM_META = [
    {'key': 'R', 'name': '现实型(R)'},
    {'key': 'I', 'name': '研究型(I)'},
    {'key': 'A', 'name': '艺术型(A)'},
    {'key': 'S', 'name': '社会型(S)'},
    {'key': 'E', 'name': '企业型(E)'},
    {'key': 'C', 'name': '常规型(C)'},
]


def calculate_holland_scores(answers):
    scores = {k: 0 for k in RIASEC}
    if not isinstance(answers, list):
        return scores
    for i, ans in enumerate(answers):
        if ans == 'A':
            scores[RIASEC[i % 6]] += 1
    return scores


def rank_holland_scores(scores):
    s = normalize_scores(scores)
    arr = [{'k': k, 'v': s[k]} for k in RIASEC]
    arr.sort(key=lambda x: (-x['v'], RIASEC.index(x['k'])))
    return arr


def get_top_three_letters(scores):
    return [r['k'] for r in rank_holland_scores(scores)[:3]]


def holland_triple_code_from_scores(scores):
    return get_unique_holland_code(scores)


def holland_top_three_riasec_sorted_from_scores(scores):
    code = ''.join(get_top_three_letters(scores))
    if len(code) != 3:
        return code
    letters = list(code.upper())
    letters.sort(key=lambda c: RIASEC.index(c))
    return ''.join(letters)


def pick_holland_triple_careers(career_map, code):
    if not career_map or not code or len(code) != 3:
        return None
    return career_map.get(code)


def dim_label(key):
    for d in DIM_META:
        if d['key'] == key:
            return d['name']
    return key


def build_holland_dim_cards_top_three(scores, holland_dimensions):
    norm = normalize_scores(scores)
    keys = get_top_three_letters(scores)
    out = []
    for k in keys:
        raw = (holland_dimensions or {}).get(k) or {}
        dim = {
            'name': raw.get('name') or dim_label(k),
            'introduction': raw.get('introduction') or '',
            'advantages': raw.get('advantages') or [],
            'disadvantages': raw.get('disadvantages') or [],
            'typical_careers': raw.get('typicalCareers') or raw.get('typical_careers') or [],
        }
        out.append({'key': k, 'score': norm[k], 'dim': dim})
    return out


def build_bar_rows(scores):
    top3 = set(get_top_three_letters(scores))
    rows = []
    for d in DIM_META:
        v = normalize_scores(scores).get(d['key'], 0)
        rows.append({
            'key': d['key'],
            'name': d['name'],
            'value': v,
            'pct': round((v / MAX_SCORE) * 100),
            'in_top3': d['key'] in top3,
        })
    return rows
