# bfi2_calc.py — BFI-2 计分（与小程序 大五人格算法.js 一致）
from __future__ import annotations

from bfi2_loader import load_dimensions, load_match_meta, load_norms, load_questions

MAIN_ORDER = ['E', 'A', 'C', 'N', 'O']
FACET_ORDER = {
    'E': ['sociability', 'assertiveness', 'energyLevel'],
    'A': ['compassion', 'respectfulness', 'trust'],
    'C': ['organization', 'productiveness', 'responsibility'],
    'N': ['anxiety', 'depression', 'emotionalVolatility'],
    'O': ['aestheticSensitivity', 'intellectualCuriosity', 'creativeImagination'],
}


def _reverse_score(score):
    return 6 - int(score)


def _rating_from_norms(score, norms_block):
    bands = ['veryLow', 'low', 'medium', 'high', 'veryHigh']
    for key in bands:
        band = norms_block.get(key) or {}
        if score <= int(band.get('max', 0)):
            return {
                'level': key,
                'label': band.get('label', key),
                'score': score,
            }
    last = norms_block.get('veryHigh') or {}
    return {
        'level': 'veryHigh',
        'label': last.get('label', '很高'),
        'score': score,
    }


def _match_percentage(dims, weights):
    total = 0.0
    for key, weight in weights.items():
        w = float(weight)
        if key.startswith('reverse_'):
            dim = key.replace('reverse_', '')
            total += (60 - float(dims.get(dim, 0))) * w
        else:
            total += float(dims.get(key, 0)) * w
    pct = max(0, min(100, total * (100 / 60)))
    return round(pct * 10) / 10


def _all_match_scores(dims):
    return {
        'teamRoles': {
            'leader': _match_percentage(dims, {'E': 0.30, 'C': 0.25, 'reverse_N': 0.20, 'O': 0.15, 'reverse_A': 0.10}),
            'executor': _match_percentage(dims, {'C': 0.40, 'reverse_N': 0.20, 'A': 0.20, 'E': 0.10, 'reverse_O': 0.10}),
            'creator': _match_percentage(dims, {'O': 0.45, 'reverse_C': 0.20, 'reverse_A': 0.15, 'E': 0.10, 'N': 0.10}),
            'coordinator': _match_percentage(dims, {'A': 0.40, 'E': 0.30, 'reverse_N': 0.20, 'C': 0.05, 'O': 0.05}),
            'supporter': _match_percentage(dims, {'A': 0.35, 'reverse_N': 0.30, 'C': 0.20, 'reverse_E': 0.10, 'O': 0.05}),
            'critic': _match_percentage(dims, {'reverse_A': 0.35, 'O': 0.30, 'reverse_N': 0.20, 'C': 0.15}),
        },
        'workEnvironments': {
            'innovative': _match_percentage(dims, {'O': 0.40, 'E': 0.20, 'reverse_N': 0.20, 'reverse_C': 0.10, 'A': 0.10}),
            'traditional': _match_percentage(dims, {'C': 0.35, 'A': 0.25, 'reverse_O': 0.20, 'reverse_N': 0.15, 'E': 0.05}),
            'highPressure': _match_percentage(dims, {'reverse_N': 0.40, 'C': 0.30, 'E': 0.15, 'reverse_A': 0.10, 'O': 0.05}),
            'teamOriented': _match_percentage(dims, {'A': 0.35, 'E': 0.30, 'reverse_N': 0.20, 'C': 0.10, 'O': 0.05}),
            'independent': _match_percentage(dims, {'reverse_E': 0.35, 'C': 0.30, 'O': 0.20, 'reverse_N': 0.10, 'A': 0.05}),
        },
        'careerTypes': {
            'management': _match_percentage(dims, {'E': 0.30, 'C': 0.25, 'reverse_N': 0.20, 'O': 0.15, 'reverse_A': 0.10}),
            'technical': _match_percentage(dims, {'C': 0.35, 'O': 0.25, 'reverse_E': 0.20, 'reverse_N': 0.15, 'A': 0.05}),
            'service': _match_percentage(dims, {'A': 0.40, 'E': 0.30, 'reverse_N': 0.20, 'C': 0.08, 'O': 0.02}),
            'creative': _match_percentage(dims, {'O': 0.50, 'N': 0.20, 'reverse_C': 0.15, 'reverse_A': 0.10, 'E': 0.05}),
            'sales': _match_percentage(dims, {'E': 0.45, 'C': 0.20, 'reverse_A': 0.15, 'reverse_N': 0.15, 'O': 0.05}),
        },
    }


def _match_sections_flat(match_scores, meta):
    sections = []
    for sec_key, title in (
        ('teamRoles', '团队角色匹配度'),
        ('workEnvironments', '工作环境匹配度'),
        ('careerTypes', '职业类型匹配度'),
    ):
        items_meta = {m['key']: m for m in (meta.get(sec_key) or [])}
        scores = match_scores.get(sec_key) or {}
        rows = []
        for key, pct in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            m = items_meta.get(key, {})
            rows.append({
                'key': key,
                'label': m.get('label', key),
                'intro': m.get('intro', ''),
                'percent': min(100, max(0, round(float(pct)))),
            })
        sections.append({'id': sec_key, 'title': title, 'rows': rows})
    return sections


def run_bfi2_test(answers_1_5):
    """answers_1_5: 长度 60，每项为 '1'~'5' 或空"""
    questions = load_questions()
    dimensions_meta = load_dimensions()
    norms = load_norms()
    n = 60
    if len(answers_1_5) < n:
        answers_1_5 = list(answers_1_5) + [''] * (n - len(answers_1_5))
    answers_1_5 = answers_1_5[:n]

    by_id = {}
    for i, q in enumerate(questions):
        raw = answers_1_5[i]
        if raw in ('1', '2', '3', '4', '5'):
            by_id[q['id']] = int(raw)

    dims = {k: 0 for k in MAIN_ORDER}
    facets = {d: {f: 0 for f in FACET_ORDER[d]} for d in MAIN_ORDER}

    for q in questions:
        raw = by_id.get(q['id'])
        if raw is None:
            continue
        score = _reverse_score(raw) if q.get('reverse') else raw
        dim = q['dimension']
        facet = q['facet']
        dims[dim] += score
        facets[dim][facet] += score

    dim_ratings = {
        d: _rating_from_norms(dims[d], norms.get('mainDimensions') or {})
        for d in MAIN_ORDER
    }
    facet_ratings = {}
    for d in MAIN_ORDER:
        for f in FACET_ORDER[d]:
            key = f'{d}_{f}'
            facet_ratings[key] = _rating_from_norms(
                facets[d][f],
                norms.get('facets') or {},
            )

    dimension_reports = []
    for d in MAIN_ORDER:
        meta = dimensions_meta.get(d, {})
        rating = dim_ratings[d]
        facet_rows = []
        for f in FACET_ORDER[d]:
            fr = facet_ratings[f'{d}_{f}']
            facet_name = (meta.get('facets') or {}).get(f, f)
            facet_rows.append({
                'code': f,
                'name': facet_name,
                'score': fr['score'],
                'level': fr['level'],
                'label': fr['label'],
            })
        desc = (meta.get('description') or {}).get(
            'high' if rating['level'] in ('high', 'veryHigh') else (
                'low' if rating['level'] in ('low', 'veryLow') else 'medium'
            ),
            '',
        )
        dimension_reports.append({
            'id': d,
            'name': meta.get('name', d),
            'nameEn': meta.get('nameEn', ''),
            'score': rating['score'],
            'level': rating['level'],
            'label': rating['label'],
            'description': desc,
            'facets': facet_rows,
        })

    match_scores = _all_match_scores(dims)
    match_sections = _match_sections_flat(match_scores, load_match_meta())

    return {
        'dimensions': dims,
        'facets': facets,
        'dimensionRatings': dim_ratings,
        'facetRatings': facet_ratings,
        'dimensionReports': dimension_reports,
        'matchScores': match_scores,
        'matchSections': match_sections,
    }
