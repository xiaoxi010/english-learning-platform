# subject_loader.py - 学科能力 / 综合能力 JSON
import json
import os
from functools import lru_cache

_BASE = os.path.dirname(os.path.abspath(__file__))
ABILITY_PATHS = [
    os.path.join(_BASE, 'data', 'subjectAbilityData.json'),
    os.path.join(
        r'C:\Users\HP\Desktop\吉致生涯\吉致生涯\life_code\miniprogram\data',
        'subjectAbilityData.json',
    ),
]
COMP_PATHS = [
    os.path.join(_BASE, 'data', 'comprehensive.json'),
    os.path.join(_BASE, 'data', '综合能力评级.json'),
    os.path.join(
        r'e:\xwechat_files\wxid_6kz7tqac90kx22_67a2\msg\file\2026-06',
        '综合能力评级.json',
    ),
    os.path.join(
        r'C:\Users\HP\Desktop\吉致生涯\吉致生涯\life_code\miniprogram\data',
        'comprehensive.json',
    ),
]


def _load_json(paths):
    for path in paths:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f'[subject] 读取失败 {path}: {e}')
    return None


@lru_cache(maxsize=1)
def load_ability_json():
    data = _load_json(ABILITY_PATHS)
    if data is None:
        print('[subject] 未找到 subjectAbilityData.json')
    return data


@lru_cache(maxsize=1)
def load_comprehensive_json():
    return _load_json(COMP_PATHS)


def ability_ready():
    return load_ability_json() is not None


def comprehensive_ready():
    return load_comprehensive_json() is not None


def normalize_ability_list(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw.get('学科能力数据'), list):
        return raw['学科能力数据']
    return []


def normalize_comprehensive_list(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if raw.get('学科码') and raw.get('综合能力数据'):
        return [raw]
    if isinstance(raw.get('综合能力数据'), list):
        return raw['综合能力数据']
    if isinstance(raw.get('综合能力评级'), list):
        return raw['综合能力评级']
    return []


def find_ability_by_code(raw, subject_code):
    code = str(subject_code or '').strip()
    for row in normalize_ability_list(raw):
        if str(row.get('学科码') or row.get('学科码', '')).strip() == code:
            return row
    o = raw.get('学科能力数据') if isinstance(raw, dict) else None
    if isinstance(o, dict) and not isinstance(o, list):
        row = o.get(code) or o.get(int(code)) if code.isdigit() else None
        if row is None:
            return None
        if isinstance(row, dict) and not isinstance(row, list):
            if str(row.get('学科码', '')).strip():
                return row
            return {'学科码': code, **row}
        return {'学科码': code, '学科数据': row}
    return None


def find_comprehensive_by_code(raw, subject_code):
    if not raw:
        return None
    code = str(subject_code or '').strip()
    for row in normalize_comprehensive_list(raw):
        if str(row.get('学科码') or '').strip() == code:
            return row
    o = raw.get('综合能力数据') if isinstance(raw, dict) else None
    if isinstance(o, dict) and not isinstance(o, list):
        row = o.get(code) or (o.get(int(code)) if code.isdigit() else None)
        if row is None:
            return None
        if isinstance(row, dict):
            if str(row.get('学科码', '')).strip():
                return row
            return {'学科码': code, '综合能力数据': row}
        return {'学科码': code, '综合能力数据': row}
    return None
