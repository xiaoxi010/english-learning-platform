# jilin_enrollment_plan_loader.py — 吉林省招生计划 JSON 查询
"""加载吉林省 2025 招生计划（普通类 + 体育艺术类），供高考测评表查询。"""
import json
import os
import re

_BASE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_BASE, 'data', 'college_major_scores')

_FILES = {
    'jilin_2025': {
        'province': '吉林',
        'year': 2025,
        'title': '吉林省2025招生计划查询',
        'paths': [
            os.path.join(_DATA_DIR, '吉林省_2025招生计划.json'),
            os.path.join(_DATA_DIR, '吉林省_2025招生计划_体育艺术类.json'),
        ],
    },
}

DISPLAY_COLUMNS = [
    {'key': 'major_code', 'label': '专业代号'},
    {'key': 'school_name', 'label': '院校'},
    {'key': 'major_name', 'label': '专业'},
    {'key': 'batch', 'label': '批次'},
    {'key': 'category', 'label': '类别'},
    {'key': 'duration', 'label': '学制'},
    {'key': 'plan_count', 'label': '招生人数'},
    {'key': 'reselect_subjects', 'label': '再选选科'},
    {'key': 'enrollment_gender', 'label': '招生性别'},
    {'key': 'enrollment_remark', 'label': '招生备注'},
    {'key': 'major_note', 'label': '专业备注'},
]

_FIELD_MAP = {
    '专业代号': 'major_code',
    '大学': 'school_name',
    '专业': 'major_name',
    '批次': 'batch',
    '类别': 'category',
    '学制': 'duration',
    '招生人数': 'plan_count',
    '再选选科要求': 'reselect_subjects',
    '招生性别': 'enrollment_gender',
    '招生备注': 'enrollment_remark',
    '专业备注': 'major_note',
}

_CACHE = {}

FILTER_OPTIONS = {
    'batch': ['', '提前A', '提前B', '本科', '专科'],
    'category': [
        '', '历史类', '物理类', '历史体育类', '物理体育类', '历史艺术类', '物理艺术类',
    ],
    'reselect_subjects': [
        '', '不限', '思想政治', '化学', '生物', '地理', '化学/生物',
    ],
    'enrollment_gender': ['', '暂无', '只招男生', '只招女生'],
}

_FILTER_LABELS = {
    'batch': '批次',
    'category': '类别',
    'reselect_subjects': '选课限制',
    'enrollment_gender': '招收性别',
}


def _normalize_record(rec):
    from jilin_2025_enrollment_loader import _norm_text_spaces, _norm_entity_name

    out = {}
    for cn, en in _FIELD_MAP.items():
        val = rec.get(cn)
        if val is None or val == '':
            out[en] = ''
        elif en in ('school_name', 'major_name'):
            out[en] = _norm_entity_name(str(val))
        elif isinstance(val, str):
            out[en] = _norm_text_spaces(val)
        else:
            out[en] = val
    return out


def _load_merged(dataset_id='jilin_2025'):
    if dataset_id in _CACHE:
        return _CACHE[dataset_id]
    meta = _FILES.get(dataset_id)
    if not meta:
        _CACHE[dataset_id] = None
        return None
    records = []
    for path in meta['paths']:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for rec in data.get('records') or []:
                records.append(_normalize_record(rec))
        except (json.JSONDecodeError, OSError):
            continue
    payload = {
        'id': dataset_id,
        'province': meta['province'],
        'year': meta['year'],
        'title': meta['title'],
        'count': len(records),
        'columns': DISPLAY_COLUMNS,
        'records': records,
    }
    _CACHE[dataset_id] = payload
    return payload


def dataset_status(dataset_id='jilin_2025'):
    meta = _FILES.get(dataset_id)
    if not meta:
        return {'available': False, 'count': 0}
    count = 0
    for path in meta['paths']:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                count += int(json.load(f).get('count') or 0)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
    return {
        'available': count > 0,
        'count': count,
        'province': meta['province'],
        'year': meta['year'],
        'title': meta['title'],
    }


def get_filter_options(dataset_id='jilin_2025'):
    """返回筛选项（首项为空表示「全部」）。"""
    data = _load_merged(dataset_id)
    if not data:
        return {'ok': False, 'filters': {}}
    opts = {}
    for key, defaults in FILTER_OPTIONS.items():
        seen = {v for v in defaults if v}
        dynamic = sorted({
            str(r.get(key) or '').strip()
            for r in data['records']
            if str(r.get(key) or '').strip()
        })
        ordered = ['']
        for v in defaults[1:]:
            if v in seen:
                ordered.append(v)
                seen.discard(v)
        for v in dynamic:
            if v not in ordered:
                ordered.append(v)
        opts[key] = ordered
    return {'ok': True, 'filters': opts, 'labels': _FILTER_LABELS}


def _has_query(school_q, major_q, filters):
    if school_q or major_q:
        return True
    return any((filters or {}).get(k) for k in FILTER_OPTIONS)


def _match_filters(rec, filters):
    for key in FILTER_OPTIONS:
        val = (filters or {}).get(key) or ''
        if not val:
            continue
        if str(rec.get(key) or '').strip() != val:
            return False
    return True


def search_records(
    dataset_id='jilin_2025',
    school='',
    major='',
    limit=100,
    batch='',
    category='',
    reselect_subjects='',
    enrollment_gender='',
):
    data = _load_merged(dataset_id)
    if not data:
        return {'ok': False, 'message': '招生计划数据不存在', 'records': [], 'total': 0}

    school_q = (school or '').strip().lower()
    major_q = (major or '').strip().lower()
    filters = {
        'batch': (batch or '').strip(),
        'category': (category or '').strip(),
        'reselect_subjects': (reselect_subjects or '').strip(),
        'enrollment_gender': (enrollment_gender or '').strip(),
    }
    if not _has_query(school_q, major_q, filters):
        return {
            'ok': True,
            'total': 0,
            'records': [],
            'columns': data['columns'],
            'title': data['title'],
            'province': data['province'],
            'year': data['year'],
        }

    def _bits(text):
        return [b for b in re.split(r'[\s,，、]+', text) if b]

    school_bits = _bits(school_q) if school_q else []
    major_bits = _bits(major_q) if major_q else []
    matched = []
    total = 0
    for rec in data['records']:
        if school_bits:
            name = str(rec.get('school_name') or '').lower()
            if not all(bit in name for bit in school_bits):
                continue
        if major_bits:
            blob = ' '.join([
                str(rec.get('major_name') or ''),
                str(rec.get('major_code') or ''),
                str(rec.get('major_note') or ''),
            ]).lower()
            if not all(bit in blob for bit in major_bits):
                continue
        if not _match_filters(rec, filters):
            continue
        total += 1
        if len(matched) < limit:
            matched.append(rec)

    return {
        'ok': True,
        'total': total,
        'records': matched,
        'columns': data['columns'],
        'title': data['title'],
        'province': data['province'],
        'year': data['year'],
    }


def list_schools(dataset_id='jilin_2025', query='', limit=60):
    data = _load_merged(dataset_id)
    if not data:
        return {'ok': False, 'schools': []}
    q = (query or '').strip().lower()
    seen = set()
    schools = []
    for rec in data['records']:
        name = str(rec.get('school_name') or '').strip()
        if not name or name in seen:
            continue
        if q and q not in name.lower():
            continue
        seen.add(name)
        schools.append(name)
        if len(schools) >= limit:
            break
    schools.sort()
    return {'ok': True, 'schools': schools}
