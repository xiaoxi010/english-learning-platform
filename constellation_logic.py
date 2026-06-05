# constellation_logic.py — 星血（星座×血型）分析
from __future__ import annotations

import re
from datetime import datetime

from constellation_loader import data_ready, load_constellation_data
from digital_talent_logic import format_birth_display

BLOOD_TYPES = ('A', 'B', 'AB', 'O')
COMBO_SECTION_LABELS = (
    '性格特质分析',
    '爱情与情感',
    '事业与财富',
    '人际关系',
    '成长建议',
    '综合建议',
)


def normalize_blood_type(raw) -> str:
    if raw is None or raw == '':
        return ''
    s = re.sub(r'\s+', '', str(raw).strip())
    u = s.upper()
    if u in ('AB', 'AB型', 'AB型血'):
        return 'AB'
    if u in ('A', 'A型', 'A型血'):
        return 'A'
    if u in ('B', 'B型', 'B型血'):
        return 'B'
    if u in ('O', 'O型', 'O型血'):
        return 'O'
    return ''


def get_constellation(birth_str: str) -> str | None:
    if not birth_str:
        return None
    date_str = str(birth_str).replace('/', '-')
    parts = date_str.split('-')
    if len(parts) < 3:
        return None
    try:
        month = int(parts[1])
        day = int(parts[2])
    except ValueError:
        return None
    num = month * 100 + day
    if num >= 1221 or num <= 119:
        return '摩羯座'
    if num >= 1122:
        return '射手座'
    if num >= 1023:
        return '天蝎座'
    if num >= 923:
        return '天秤座'
    if num >= 823:
        return '处女座'
    if num >= 723:
        return '狮子座'
    if num >= 621:
        return '巨蟹座'
    if num >= 521:
        return '双子座'
    if num >= 420:
        return '金牛座'
    if num >= 320:
        return '白羊座'
    if num >= 219:
        return '双鱼座'
    if num >= 120:
        return '水瓶座'
    return '未知星座'


def _lookup(table: dict, key: str, default=''):
    if not table or not key:
        return default
    v = table.get(key)
    return v if v is not None else default


def _collect_constellation_list(data: dict, prefix: str, constellation: str, max_n: int = 8):
    items = []
    base = _lookup(data.get(prefix) or {}, constellation, '')
    if base and str(base).strip():
        items.append(str(base).strip())
    for i in range(1, max_n + 1):
        tbl = data.get(f'{prefix}_{i}') or {}
        v = tbl.get(constellation)
        if v and str(v).strip():
            items.append(str(v).strip())
    return items


def perform_analysis(birthday: str, blood_type: str) -> dict:
    data = load_constellation_data()
    if not data:
        return {'error': '星座资料未就绪，请将 constellation.json 放到 data 目录'}

    blood = normalize_blood_type(blood_type)
    constellation = get_constellation(birthday)
    if not constellation:
        return {'error': '生日格式不正确'}
    if not blood:
        return {'error': '请选择血型'}

    result = {
        'birthday': birthday,
        'bloodType': blood,
        'constellation': constellation,
    }

    result['attribute'] = _lookup(data.get('constellation_attribute') or {}, constellation)
    result['form'] = _lookup(data.get('constellation_form') or {}, constellation)
    result['protect'] = _lookup(data.get('constellation_protect') or {}, constellation)
    result['fit'] = _lookup(data.get('constellation_fit') or {}, constellation)
    form = result['form']
    result['four_phase'] = _lookup(data.get('four_phase_constellation') or {}, form)
    result['characteristic_feature'] = _lookup(
        data.get('characteristic_feature') or {}, constellation
    )
    result['character_trait'] = _lookup(data.get('character_trait') or {}, constellation)
    result['work'] = _lookup(data.get('work') or {}, constellation)
    result['ideal_career'] = _lookup(data.get('ideal_career') or {}, constellation)
    result['child_study'] = _lookup(data.get('child_study') or {}, constellation)
    result['special_abilities'] = _collect_constellation_list(
        data, 'special_ability', constellation
    )
    result['words'] = _collect_constellation_list(data, 'word', constellation)

    result['life_habit'] = _lookup(data.get('life_habit') or {}, blood)
    result['career_analysis'] = _lookup(data.get('career_analysis') or {}, blood)
    result['suggestion_for_parents'] = _lookup(
        data.get('suggestion_for_parents') or {}, blood
    )
    result['characteristic_feature_blood'] = _lookup(
        data.get('characteristic_feature_blood') or {}, blood
    )

    result['study_features'] = []
    for i in range(1, 5):
        feat = (data.get(f'study_feature_{i}') or {}).get(blood)
        if feat:
            result['study_features'].append(str(feat))

    blood_analysis = _lookup(data.get('blood_characteristic_analysis') or {}, blood)
    traits = [t.strip() for t in blood_analysis.split(',') if t.strip()]
    result['blood_characteristic'] = traits
    detail_tbl = data.get('blood_characteristic_analysis_detail') or {}
    result['blood_characteristic_details'] = []
    for trait in traits:
        detail = detail_tbl.get(trait)
        if detail:
            result['blood_characteristic_details'].append(
                {'trait': trait, 'detail': detail}
            )

    key = f'{blood}-{constellation}'
    result['blood_constellation_key'] = key
    analyses = []
    for i in range(1, 7):
        short_tbl = data.get(f'blood_constellation_{i}') or {}
        txt_tbl = data.get(f'blood_constellation_{i}_txt') or {}
        short_a = (short_tbl.get(key) or '').strip()
        detail_a = (txt_tbl.get(key) or '').strip()
        if short_a or detail_a:
            analyses.append({
                'title': short_a,
                'detail': detail_a,
                'section': COMBO_SECTION_LABELS[i - 1] if i <= len(COMBO_SECTION_LABELS) else f'分析{i}',
            })
    result['blood_constellation_analyses'] = analyses
    return result


def build_constellation_report(user_name: str, year: int, month: int, day: int, blood_type: str) -> dict:
    if not data_ready():
        raise ValueError('星座资料未加载，请将 constellation.json 放到 data 目录')

    blood = normalize_blood_type(blood_type)
    if blood not in BLOOD_TYPES:
        raise ValueError('请选择有效血型（A / B / AB / O）')

    birthday = format_birth_display(year, month, day)
    analysis = perform_analysis(birthday, blood)
    if analysis.get('error'):
        raise ValueError(analysis['error'])

    display_name = (user_name or '').strip() or '朋友'
    attr = analysis.get('attribute') or ''
    summary = analysis['constellation']
    if blood:
        summary += f' · {blood}型'
    if attr:
        summary += f' · {attr}'

    now = datetime.now()
    return {
        'user_name': display_name,
        'summary': f'{display_name} · {summary}',
        'birth_display': f'{year}年{month}月{day}日',
        'birthday': birthday,
        'calculate_time': now.strftime('%Y-%m-%d %H:%M'),
        'report_id': f'XB-{now.strftime("%Y%m%d")}-{int(now.timestamp()) % 100000:05d}',
        'analysis': analysis,
        'data_ready': True,
    }
