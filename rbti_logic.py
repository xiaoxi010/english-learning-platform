# rbti_logic.py
from datetime import datetime

from rbti_calc import VALID_ANS, calculate_rbti
from rbti_loader import load_dimension_texts, load_meta, load_personalities, load_questions

MAX_SCORE = 31


def parse_answers(form, total):
    answers = []
    for i in range(total):
        v = (form.get(f'ans_{i}') or '').strip().upper()
        if v not in VALID_ANS:
            answers.append(None)
        else:
            answers.append(v)
    return answers


def _score_to_ten(score, max_score):
    if max_score <= 0:
        return '0.0'
    return f'{(score / max_score) * 10:.1f}'


def generate_dimension_results(scores):
    texts = load_dimension_texts()
    rows = []
    for i in range(1, 13):
        code = f'C{i}'
        score = scores.get(code, 0)
        max_s = MAX_SCORE
        pct = round((score / max_s) * 100) if max_s else 0
        level = 'H' if score >= max_s / 2 else 'L'
        dim = texts.get(code) or {}
        level_block = dim.get(level) or {}
        rows.append({
            'code': code,
            'name': dim.get('name', code),
            'subtitle': dim.get('subtitle', ''),
            'score': score,
            'maxScore': max_s,
            'percentage': pct,
            'level': level,
            'levelName': level_block.get('level', ''),
            'desc': level_block.get('desc', ''),
            'scoreTen': _score_to_ten(score, max_s),
        })
    return rows


def generate_summary(scores):
    results = generate_dimension_results(scores)
    high_dims = [r['name'] for r in results if r['level'] == 'H']
    low_dims = [r['name'] for r in results if r['level'] == 'L']

    if len(high_dims) >= 8:
        return '你是一个纯度很高的抽象人，各方面都偏离了正常人类范畴。建议：继续保持，世界需要多样性。'
    if len(high_dims) >= 5:
        top = '、'.join(high_dims[:3])
        return f'你在{top}方面比较突出，其他方面还算正常。属于「间歇性发癫，持续性正常」类型。'
    if len(high_dims) >= 2:
        top = '和'.join(high_dims[:2])
        return f'你主要在{top}方面有点大病，其他方面都挺正常的。属于「局部有病，整体健康」。'
    if len(high_dims) == 0:
        return '你各项指标都在正常范围内，是这套题里罕见的正常人。建议：取关这个测试，去测点正经的。'
    return f'你只有{high_dims[0]}方面稍微有点离谱，整体还算是个正常人。建议：继续保持，别被带歪。'


def get_personality(type_code):
    personalities = load_personalities()
    p = personalities.get(type_code)
    if p:
        return dict(p)
    return {
        'name': '自定义人格',
        'emoji': '🎲',
        'desc': (
            '你是一个无法被归类的存在。RBTI 的四种倾向在你身上以一种神秘而复杂的方式混合，'
            '形成了一款市面上没有的限定配方。年度关键词：随便。'
        ),
    }


def build_rbti_report(user_name, answers):
    questions = load_questions()
    n = len(questions)
    if n != 31:
        raise ValueError('RBTI 题库未加载完整（需 31 题）')

    if len(answers) < n:
        answers = list(answers) + [None] * (n - len(answers))
    answers = answers[:n]

    for i, a in enumerate(answers):
        if a is None or a not in VALID_ANS:
            raise ValueError(f'请完成第 {i + 1} 题')

    calc = calculate_rbti(answers)
    personality = get_personality(calc['typeCode'])
    dimension_rows = generate_dimension_results(calc['scores'])
    summary_text = generate_summary(calc['scores'])
    tag_list = [r['name'] for r in dimension_rows if r['level'] == 'H'][:5]

    meta = load_meta()
    dims = calc['dimensions']
    total = calc['total'] or 1
    axis_bars = []
    for ax in meta.get('axes', []):
        key = ax.get('key', '')
        val = dims.get(key, 0)
        axis_bars.append({
            'key': key,
            'label': ax.get('label', key),
            'score': val,
            'pct': round((val / total) * 100, 1) if total else 0,
            'level': 'H' if val >= total / 4 else 'L',
        })

    now = datetime.now()
    return {
        'user_name': user_name,
        'summary': f'{user_name} · {calc["typeCode"]} · {personality.get("name", "")}',
        'calculate_time': now.strftime('%Y-%m-%d %H:%M'),
        'report_id': f'RBT-{now.strftime("%Y%m%d")}-{int(now.timestamp()) % 100000:05d}',
        'meta': meta,
        'calc': calc,
        'personality': personality,
        'dimension_rows': dimension_rows,
        'summary_text': summary_text,
        'tag_list': tag_list,
        'axis_bars': axis_bars,
        'data_ready': True,
    }
