# score_rank_loader.py — 各省一分一段（对齐 miniprogram/utils/scoreRankCloud.js）
import json
import os
from functools import lru_cache

_BASE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_BASE, 'data', 'score_rank')

PROVINCE_FILES = {
    '吉林': '吉林省2025一分一段.json',
    '上海': '上海_2025一分一段.json',
    '云南': '云南_2025一分一段.json',
    '内蒙古': '内蒙古_2025一分一段.json',
    '北京': '北京_2025一分一段.json',
    '四川': '四川_2025一分一段.json',
    '天津': '天津_2025一分一段.json',
    '宁夏': '宁夏_2025一分一段.json',
    '安徽': '安徽_2025一分一段.json',
    '山东': '山东_2025一分一段.json',
    '山西': '山西_2025一分一段.json',
    '广东': '广东_2025一分一段.json',
    '广西': '广西_2025一分一段.json',
    '新疆': '新疆_2025一分一段.json',
    '江苏': '江苏_2025一分一段.json',
    '江西': '江西_2025一分一段.json',
    '河北': '河北_2025一分一段.json',
    '河南': '河南_2025一分一段.json',
    '浙江': '浙江_2025一分一段.json',
    '海南': '海南_2025一分一段.json',
    '湖北': '湖北_2025一分一段.json',
    '湖南': '湖南_2025一分一段.json',
    '甘肃': '甘肃_2025一分一段.json',
    '福建': '福建_2025一分一段.json',
    '贵州': '贵州_2025一分一段.json',
    '辽宁': '辽宁_2025一分一段.json',
    '重庆': '重庆_2025一分一段.json',
    '陕西': '陕西_2025一分一段.json',
    '青海': '青海_2025一分一段.json',
    '黑龙江': '黑龙江_2025一分一段.json',
}

PROVINCE_LIST = list(PROVINCE_FILES.keys())
PROVINCES_USE_LIKE_WEN = ['新疆']
PROVINCES_USE_ZONGHE = ['上海']

_EXTRA_DIRS = [
    os.environ.get('SCORE_RANK_DATA_DIR', '').strip(),
    os.path.join(r'C:\Users\HP\Desktop\一分一段表\一分一段表'),
    os.path.join(r'C:\Users\HP\Desktop\一分一段表'),
    os.path.join(
        r'C:\Users\HP\Desktop\吉致生涯\吉致生涯\life_code\miniprogram\data\score_rank',
    ),
]

# 云存储标准名之外的本地下载文件名
PROVINCE_FILE_ALIASES = {
    '吉林': ['吉林_2025一分一段.json', '吉林省2025一分一段.json'],
}


def _resolve_path(filename, province=None):
    if not filename:
        return None
    names = [filename]
    if province and province in PROVINCE_FILE_ALIASES:
        for alt in PROVINCE_FILE_ALIASES[province]:
            if alt not in names:
                names.append(alt)
    for base in [_DATA_DIR] + [d for d in _EXTRA_DIRS if d]:
        for name in names:
            path = os.path.join(base, name)
            if os.path.isfile(path):
                return path
    return os.path.join(_DATA_DIR, filename)


def province_subject_labels(province):
    use_z = province in PROVINCES_USE_ZONGHE
    use_like = province in PROVINCES_USE_LIKE_WEN
    if use_z:
        return {
            'label_a': '综合',
            'label_b': '',
            'show_subject_row': False,
            'default_subject': 'physics',
        }
    if use_like:
        return {
            'label_a': '理科',
            'label_b': '文科',
            'show_subject_row': True,
            'default_subject': 'physics',
        }
    return {
        'label_a': '物理',
        'label_b': '历史',
        'show_subject_row': True,
        'default_subject': 'physics',
    }


def parse_score_rank_data(raw):
    if not raw or not isinstance(raw, dict):
        return None
    result = {'physics': {}, 'history': {}}

    def normalize(obj):
        out = {}
        for k, v in obj.items():
            score = str(k)
            if isinstance(v, dict) and ('rank' in v or 'same_score_count' in v):
                out[score] = {
                    'rank': v.get('rank') if v.get('rank') is not None else v.get('same_score_count'),
                    'same_score_count': v.get('same_score_count')
                    if isinstance(v.get('same_score_count'), (int, float))
                    else None,
                }
            elif isinstance(v, (int, float)):
                out[score] = {'rank': v, 'same_score_count': None}
        return out

    if isinstance(raw.get('物理'), dict):
        result['physics'] = normalize(raw['物理'])
    if isinstance(raw.get('历史'), dict):
        result['history'] = normalize(raw['历史'])
    if isinstance(raw.get('理科'), dict) and not result['physics']:
        result['physics'] = normalize(raw['理科'])
    if isinstance(raw.get('文科'), dict) and not result['history']:
        result['history'] = normalize(raw['文科'])
    if isinstance(raw.get('综合'), dict):
        zonghe = normalize(raw['综合'])
        if not result['physics']:
            result['physics'] = zonghe
        if not result['history']:
            result['history'] = zonghe
    if isinstance(raw.get('physics'), dict) and not result['physics']:
        result['physics'] = normalize(raw['physics'])
    if isinstance(raw.get('history'), dict) and not result['history']:
        result['history'] = normalize(raw['history'])
    return result


@lru_cache(maxsize=64)
def load_score_rank(province):
    filename = PROVINCE_FILES.get(province)
    if not filename:
        return None
    path = _resolve_path(filename, province)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            raw = json.load(f)
        return parse_score_rank_data(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f'[score_rank] 读取失败 {path}: {e}')
        return None


def province_data_available(province):
    filename = PROVINCE_FILES.get(province)
    if not filename:
        return False
    path = _resolve_path(filename, province)
    return os.path.isfile(path)


def list_provinces_status():
    return [
        {
            'name': p,
            'available': province_data_available(p),
            'file': PROVINCE_FILES[p],
            **province_subject_labels(p),
        }
        for p in PROVINCE_LIST
    ]


def get_rank_by_score(score, subject, data):
    if not data:
        return None
    table = data.get('physics') if subject == 'physics' else data.get('history')
    if not table:
        return None
    try:
        s = str(int(score))
    except (TypeError, ValueError):
        return None
    return table.get(s)


def lookup(province, subject, score):
    data = load_score_rank(province)
    if not data:
        return {
            'ok': False,
            'error': 'data_missing',
            'message': f'未找到 {province} 一分一段数据，请将云存储 JSON 放入 data/score_rank/',
        }
    item = get_rank_by_score(score, subject, data)
    if not item:
        return {
            'ok': False,
            'error': 'not_found',
            'message': '该分数暂无位次记录，请核对分数或换查其他科目',
        }
    rank = item.get('rank')
    same = item.get('same_score_count')
    return {
        'ok': True,
        'rank': str(rank) if rank is not None else None,
        'same_score_count': str(same) if same is not None else None,
    }
