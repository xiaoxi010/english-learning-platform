# eysenck_calc.py — 艾克森计分与情绪模式（对齐小程序 EysenckEmotionTest）
from eysenck_loader import load_dimensions, load_meta, load_patterns, load_scoring

OPTIONS = ('是', '否', '不确定')


def calculate_raw_scores(answers, scoring=None):
    scoring = scoring or load_scoring()
    raw = {}
    dims = scoring.get('dimensions') or {}
    for dim_id, cfg in dims.items():
        score = 0.0
        for rule in cfg.get('questions') or []:
            idx = int(rule['id']) - 1
            if idx < 0 or idx >= len(answers):
                continue
            ans = answers[idx]
            if ans == '不确定':
                score += 0.5
            elif rule.get('type') == '+' and ans == '是':
                score += 1
            elif rule.get('type') == '-' and ans == '否':
                score += 1
        raw[dim_id] = score
    return raw


def generate_dimension_analysis(raw_scores, dimensions=None):
    dimensions = dimensions or load_dimensions()
    out = []
    for dim in dimensions:
        dim_id = dim['id']
        raw_score = raw_scores.get(dim_id, 0)
        sr = dim.get('scoreRange') or {}
        unstable = sr.get('unstable') or [0, 0]
        is_unstable = unstable[0] <= raw_score <= unstable[1]
        out.append({
            'id': dim_id,
            'name': dim.get('name', dim_id),
            'rawScore': raw_score,
            'score': round(raw_score * 10) / 10,
            'scoreRange': sr,
            'isUnstable': is_unstable,
            'stable': dim.get('stable') or {},
            'unstable': dim.get('unstable') or {},
        })
    return out


def analyze_emotion_pattern(dimension_status, patterns_data=None):
    patterns_data = patterns_data or load_patterns()
    typical = patterns_data.get('typicalPatterns') or []
    by_id = {p['id']: p for p in typical if p.get('id')}

    def s(key):
        return bool(dimension_status.get(key))

    matched_ids = []
    if s('guilt') and s('inferiority') and s('depression'):
        matched_ids.append('self_attack')
    if s('obsession') and s('anxiety') and not s('autonomy'):
        matched_ids.append('over_control')
    if s('hypochondria') and s('anxiety') and s('guilt'):
        matched_ids.append('somatization')
    if s('inferiority') and s('anxiety') and not s('autonomy'):
        matched_ids.append('social_avoidance')
    if s('obsession') and s('anxiety') and s('guilt'):
        matched_ids.append('perfection_anxiety')
    if not s('autonomy') and s('depression') and s('inferiority'):
        matched_ids.append('helpless')
    if s('anxiety') and s('hypochondria') and s('inferiority'):
        matched_ids.append('hyper_vigilance')
    if s('anxiety') and not s('autonomy') and s('guilt'):
        matched_ids.append('procrastination')

    main_id = 'normal_balance' if not matched_ids else matched_ids[0]
    matched_patterns = [by_id[i] for i in matched_ids if i in by_id]
    main_pattern = by_id.get(main_id)

    return {
        'matchedIds': matched_ids,
        'mainPatternId': main_id,
        'matchedPatterns': matched_patterns,
        'mainPattern': main_pattern,
    }


def run_eysenck_test(answers):
    if len(answers) != 210:
        return None
    for a in answers:
        if a not in OPTIONS:
            return None

    raw_scores = calculate_raw_scores(answers)
    dimension_analysis = generate_dimension_analysis(raw_scores)
    dimension_status = {d['id']: d['isUnstable'] for d in dimension_analysis}
    emotion_patterns = analyze_emotion_pattern(dimension_status)
    patterns_data = load_patterns()

    return {
        'meta': load_meta(),
        'rawScores': raw_scores,
        'dimensionAnalysis': dimension_analysis,
        'emotionPatterns': emotion_patterns,
        'triggerPoints': patterns_data.get('triggerPoints') or {},
    }
