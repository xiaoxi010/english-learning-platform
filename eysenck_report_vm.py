# eysenck_report_vm.py — 报告视图模型（对齐 prepareReportViewModel）
import random
from datetime import datetime

from eysenck_loader import load_scoring

DIM_STATE_STRONG = {
    'inferiority': '自卑感',
    'depression': '抑郁性',
    'anxiety': '焦虑',
    'obsession': '强迫状态',
    'autonomy': '依赖性',
    'hypochondria': '疑心病观念',
    'guilt': '负罪感',
}

DIM_STATE_LOW = {
    'inferiority': '自尊',
    'depression': '愉快',
    'anxiety': '安详',
    'obsession': '随意性',
    'autonomy': '自主性',
    'hypochondria': '健康感',
    'guilt': '无负罪感',
}

DIMENSION_BIPOLAR_TITLES = {
    'inferiority': '自卑-自尊',
    'depression': '抑郁-愉快',
    'anxiety': '焦虑-安详',
    'obsession': '强迫-随意',
    'autonomy': '依赖-自主',
    'hypochondria': '疑心病-健康感',
    'guilt': '负罪感-无负罪感',
}

MULTI_LINE_CHAR_THRESHOLD = 54


def _format_raw_score_display(raw_score):
    try:
        raw = float(raw_score)
    except (TypeError, ValueError):
        return None
    rounded = round(raw * 10) / 10
    return str(int(rounded)) if rounded == int(rounded) else f'{rounded:.1f}'


def _format_score_slash_max(raw_score, chart_max):
    mx = max(1, int(chart_max) if chart_max else 1)
    raw_str = _format_raw_score_display(raw_score)
    if raw_str is None:
        return '—'
    return f'{raw_str}/{mx}'


def _score_band_is_high(raw_score, chart_max):
    mx = max(1, int(chart_max) if chart_max else 1)
    try:
        r = float(raw_score)
    except (TypeError, ValueError):
        return None
    return r >= mx / 2


def _state_trait_label(dim_id, is_unstable):
    if is_unstable:
        return DIM_STATE_STRONG.get(dim_id, '偏高')
    return DIM_STATE_LOW.get(dim_id, '低倾向')


def prepare_report_view_model(result, user_info):
    dimension_analysis = result.get('dimensionAnalysis') or []
    emotion_patterns = result.get('emotionPatterns') or {}
    trigger_points = result.get('triggerPoints') or {
        'work': [], 'interpersonal': [], 'life': [],
    }
    scoring = load_scoring()
    dim_rules = scoring.get('dimensions') or {}

    main_pattern = emotion_patterns.get('mainPattern')
    matched_patterns = emotion_patterns.get('matchedPatterns') or []
    safe_matched = [p for p in matched_patterns if p and p.get('name')]

    stable_dims = [d for d in dimension_analysis if not d.get('isUnstable')]
    unstable_dims = [d for d in dimension_analysis if d.get('isUnstable')]
    top3_unstable = '、'.join(
        DIM_STATE_STRONG.get(d['id'], d.get('name', '')) for d in unstable_dims[:3]
    )

    total_score = 0.0
    for d in dimension_analysis:
        sr = d.get('scoreRange') or {}
        stable_range = sr.get('stable') or [1, 30]
        max_score = stable_range[1] if len(stable_range) > 1 else 30
        if d.get('isUnstable'):
            normalized = 0
        else:
            normalized = (float(d.get('rawScore', 0)) / max_score) * 100
        total_score += normalized
    total_score /= 7

    if total_score >= 80:
        level = {'icon': '🟢', 'name': '情绪健康', 'desc': '情绪调节能力良好，整体状态稳定'}
    elif total_score >= 60:
        level = {'icon': '🟡', 'name': '轻度情绪困扰', 'desc': '个别维度存在波动，可自行调节'}
    elif total_score >= 40:
        level = {'icon': '🟠', 'name': '中度情绪困扰', 'desc': '多个维度存在困扰，建议寻求支持'}
    else:
        level = {'icon': '🔴', 'name': '重度情绪困扰', 'desc': '情绪状态严重受影响，强烈建议专业干预'}

    u0 = unstable_dims[0] if unstable_dims else None
    s0 = stable_dims[0] if stable_dims else None
    u0_label = DIM_STATE_STRONG.get(u0['id'], u0.get('name', '')) if u0 else '无'
    s0_label = DIM_STATE_LOW.get(s0['id'], s0.get('name', '')) if s0 else '多个方面'
    overall_summary = (
        f'您当前的情绪状态处于{level["name"]}水平，核心问题是{u0_label}引发的一系列连锁反应。'
        f'值得肯定的是，您在{s0_label}表现良好，这是您调节情绪的重要优势。'
    )

    dimensions = []
    for d in dimension_analysis:
        dim_id = d['id']
        is_unstable = d.get('isUnstable')
        core = (d.get('unstable') if is_unstable else d.get('stable')) or {}
        core_feature = core.get('coreFeature', '')
        rules = dim_rules.get(dim_id) or {}
        chart_max = len(rules.get('questions') or [])
        sr = d.get('scoreRange') or {}
        report_short = DIM_STATE_STRONG.get(dim_id, d.get('name', ''))
        num_str = _format_raw_score_display(d.get('rawScore')) or '—'
        bipolar = DIMENSION_BIPOLAR_TITLES.get(dim_id, report_short)
        index_title = (
            f'{report_short} 指数： —' if num_str == '—'
            else f'{report_short} 指数： {num_str}/{chart_max}'
        )
        dimensions.append({
            **d,
            'chartMax': chart_max,
            'reportDimShortName': report_short,
            'dimensionBipolarTitle': bipolar,
            'dimensionIndexTitle': index_title,
            'scoreSlashMax': _format_score_slash_max(d.get('rawScore'), chart_max),
            'scoreNumeratorText': num_str,
            'scoreBandIsHigh': _score_band_is_high(d.get('rawScore'), chart_max),
            'stateTraitLabel': _state_trait_label(dim_id, is_unstable),
            'unstableRangeLabel': f"{sr.get('unstable', ['', ''])[0]}–{sr.get('unstable', ['', ''])[1]}",
            'stableRangeLabel': f"{sr.get('stable', ['', ''])[0]}–{sr.get('stable', ['', ''])[1]}",
            'shortCoreFeature': core_feature[:20] + '...',
            'shortStableFeature': (d.get('stable') or {}).get('coreFeature', '')[:30],
            'shortUnstableFeature': (d.get('unstable') or {}).get('coreFeature', '')[:30],
            'coreFeature': core_feature,
            'coreNeedMore': len(core_feature) > MULTI_LINE_CHAR_THRESHOLD,
            'behaviors': core.get('behaviors') or [],
            'positiveImpact': core.get('positiveImpact', ''),
            'potentialChallenges': core.get('potentialChallenges', ''),
            'suggestions': core.get('suggestions') or [],
        })

    now = datetime.now()
    return {
        'meta': result.get('meta') or {},
        'userName': user_info.get('userName', ''),
        'answerTime': user_info.get('answerTime', ''),
        'answerDuration': user_info.get('answerDuration', ''),
        'isValid': user_info.get('isValid', False),
        'currentDate': now.strftime('%Y%m%d'),
        'seqId': str(random.randint(0, 999)).zfill(3),
        'reportGenerateTime': now.strftime('%Y-%m-%d'),
        'mainPattern': main_pattern,
        'hasOtherPatterns': len(safe_matched) > 1,
        'otherPatterns': [
            {
                'name': p.get('name', ''),
                'shortFeatures': str(p.get('features', ''))[:40] + '...',
                'featuresFull': str(p.get('features', '')),
                'featuresNeedMore': len(str(p.get('features', ''))) > MULTI_LINE_CHAR_THRESHOLD,
            }
            for p in safe_matched[1:]
        ],
        'triggerPoints': trigger_points,
        'comprehensiveScore': str(int(round(total_score))),
        'level': level,
        'dimensions': dimensions,
        'stableDimensions': [
            {
                'name': d.get('name'),
                'shortStableFeature': (d.get('stable') or {}).get('coreFeature', '')[:30],
                'lineFull': (d.get('stable') or {}).get('coreFeature', ''),
                'lineNeedMore': len((d.get('stable') or {}).get('coreFeature', '')) > MULTI_LINE_CHAR_THRESHOLD,
            }
            for d in stable_dims
        ],
        'unstableDimensions': [
            {
                'name': d.get('name'),
                'shortUnstableFeature': (d.get('unstable') or {}).get('coreFeature', '')[:30],
                'lineFull': (d.get('unstable') or {}).get('coreFeature', ''),
                'lineNeedMore': len((d.get('unstable') or {}).get('coreFeature', '')) > MULTI_LINE_CHAR_THRESHOLD,
            }
            for d in unstable_dims
        ],
        'top3Unstable': top3_unstable,
        'overallSummary': overall_summary,
    }
