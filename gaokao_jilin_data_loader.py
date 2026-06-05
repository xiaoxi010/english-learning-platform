# gaokao_jilin_data_loader.py — 各省高考专家版 / 强基计划 Excel → JSON
"""导入专家版、强基计划 Excel；支持 data/gaokao_apply/provinces/{省名}/ 多省目录。"""
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime

from gaokao_db import (
    batch_exists,
    dataset_count as db_dataset_count,
    migrate_json_payload_to_db,
    province_db_for_batch,
    province_has_db,
    read_dataset,
    read_dataset_by_path,
    write_expert_bucket as db_write_expert_bucket,
    write_strong_base as db_write_strong_base,
)
from gaokao_json_parts import save_json_dataset
from gaokao_province_registry import (
    BATCH_ALIAS,
    DEFAULT_DATA_YEAR,
    DEFAULT_RECORD_YEAR,
    GAOKAO_DATA_DIR,
    PROVINCES_DIR,
    copy_province_sources,
    dataset_id as province_dataset_id,
    discover_expert_files,
    discover_strong_base_files,
    legacy_jilin_dataset_id,
    list_imported_provinces,
    norm_province,
    province_json_path,
    province_db_path,
    province_dir,
    province_manifest_path,
    province_slug,
    province_source_dir,
    read_manifest,
    write_manifest,
)
from score_rank_loader import PROVINCE_LIST

_BASE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_BASE, 'data', 'gaokao_apply')
_SOURCE_DIR = os.path.join(_DATA_DIR, 'source')

_DEFAULT_EXPERT_XLSX = os.path.join(
    _SOURCE_DIR, '5、2026-吉林-专家版-.xlsx',
)
_DEFAULT_STRONG_XLSX = os.path.join(
    _SOURCE_DIR, '李老师：2025年强基计划分数线 - 吉林.xlsx',
)

EXPERT_JSON = os.path.join(_DATA_DIR, 'jilin_2025_expert.json')
EXPERT_EARLY_JSON = os.path.join(_DATA_DIR, 'jilin_2025_expert_early.json')
EXPERT_UNDERGRADUATE_JSON = os.path.join(_DATA_DIR, 'jilin_2025_expert_undergraduate.json')
EXPERT_JUNIOR_JSON = os.path.join(_DATA_DIR, 'jilin_2025_expert_junior.json')
STRONG_BASE_JSON = os.path.join(_DATA_DIR, 'jilin_2025_strong_base.json')

EXPERT_BATCH_BUCKETS = {
    'early': {
        'id': 'jilin_2025_expert_early',
        'json': EXPERT_EARLY_JSON,
        'batch_label': '提前批',
        'title': '提前批',
    },
    'undergraduate': {
        'id': 'jilin_2025_expert_undergraduate',
        'json': EXPERT_UNDERGRADUATE_JSON,
        'batch_label': '本科批',
        'title': '本科批',
    },
    'junior': {
        'id': 'jilin_2025_expert_junior',
        'json': EXPERT_JUNIOR_JSON,
        'batch_label': '专科批',
        'title': '专科批',
    },
}

EXPERT_DATASET_IDS = frozenset(meta['id'] for meta in EXPERT_BATCH_BUCKETS.values())

DATASET_ALIASES = {
    'strong': 'jilin_2025_strong_base',
    'strong_base': 'jilin_2025_strong_base',
    '强基': 'jilin_2025_strong_base',
    'early': 'jilin_2025_expert_early',
    'expert_early': 'jilin_2025_expert_early',
    '提前批': 'jilin_2025_expert_early',
    'undergraduate': 'jilin_2025_expert_undergraduate',
    'expert': 'jilin_2025_expert_undergraduate',
    'expert_undergraduate': 'jilin_2025_expert_undergraduate',
    '本科批': 'jilin_2025_expert_undergraduate',
    'junior': 'jilin_2025_expert_junior',
    'expert_junior': 'jilin_2025_expert_junior',
    '专科批': 'jilin_2025_expert_junior',
    'jilin_2025_expert': 'jilin_2025_expert_undergraduate',
}

SYSTEM_TITLE = '高考报考系统'

# 专家版 64 列（与 Excel 第 3 行一致，重复列名加前缀）
EXPERT_FIELDS = [
    ('year', '年份'),
    ('source_region', '生源地'),
    ('batch', '批次'),
    ('category', '科类'),
    ('plan_category', '计划类别'),
    ('school_code', '院校代码'),
    ('school_name', '院校名称'),
    ('major_group_code', '院校专业组代码'),
    ('major_group_name', '专业组名称'),
    ('group_code', '专业组代码'),
    ('major_code', '专业代码'),
    ('major_full_name', '专业全称'),
    ('major_name', '专业名称'),
    ('major_note', '专业备注'),
    ('subject_requirement', '选科要求'),
    ('major_level', '专业层次'),
    ('plan_count', '计划人数'),
    ('duration', '学制'),
    ('tuition', '学费'),
    ('group_majors', '组内专业'),
    ('group_plan_count', '专业组计划人数'),
    ('discipline', '门类'),
    ('major_category', '专业类'),
    ('is_new', '是否新增'),
    ('g2025_enroll_count', '专业组录取人数'),
    ('g2025_min_score', '专业组最低分'),
    ('g2025_min_rank', '专业组最低位次'),
    ('m2025_enroll_count', '录取人数'),
    ('m2025_min_score', '最低分'),
    ('m2025_min_rank', '最低位次'),
    ('m2025_max_score', '最高分'),
    ('m2025_max_rank', '最高位次'),
    ('g2024_min_score', '24专业组最低分'),
    ('g2024_min_rank', '24专业组最低位次'),
    ('g2024_enroll_count', '24专业组录取人数'),
    ('m2024_min_score', '24专业最低分'),
    ('m2024_min_rank', '24专业最低位次'),
    ('m2024_enroll_count', '24专业录取人数'),
    ('m2023_min_score', '23专业最低分'),
    ('m2023_min_rank', '23专业最低位次'),
    ('m2023_enroll_count', '23专业录取人数'),
    ('school_province', '所在省'),
    ('school_city', '城市'),
    ('city_level', '城市水平标签'),
    ('school_tags', '院校标签'),
    ('school_level', '院校水平'),
    ('school_rename', '更名合并转设'),
    ('affiliation', '隶属单位'),
    ('school_type', '类型'),
    ('ownership', '公私性质'),
    ('school_edu_level', '本科/专科'),
    ('postgrad_rate', '保研率'),
    ('school_rank', '院校排名'),
    ('major_transfer', '转专业情况'),
    ('master_major_count', '全校硕士专业数'),
    ('master_majors', '全校硕士专业'),
    ('doctor_major_count', '全校博士专业数'),
    ('doctor_majors', '全校博士专业'),
    ('admission_charter_2025', '2025招生章程'),
    ('soft_rank_grade', '软科评级'),
    ('soft_rank', '软科排名'),
    ('discipline_eval', '学科评估'),
    ('major_prof_level', '专业水平'),
    ('has_master_point', '本专业硕士点'),
    ('has_doctor_point', '本专业博士点'),
]

STRONG_BASE_FIELDS = [
    ('province', '省份'),
    ('school_name', '院校名称'),
    ('major_name', '专业名称'),
    ('qualify_score', '入围分'),
    ('admit_score', '录取分'),
]

EXPERT_KEYS = [k for k, _ in EXPERT_FIELDS]
STRONG_KEYS = [k for k, _ in STRONG_BASE_FIELDS]

_DATASETS = {}
EXPERT_DATASET_IDS = frozenset()
_CACHE = {}


def _cell_str(val):
    if val is None:
        return ''
    if isinstance(val, float):
        if val != val:
            return ''
        if val == int(val):
            return str(int(val))
    return re.sub(r'\s+', ' ', str(val).strip())


def _norm_text(text):
    s = (text or '').strip()
    if not s:
        return ''
    s = re.sub(r'\s+', ' ', s)
    while True:
        ns = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', s)
        if ns == s:
            break
        s = ns
    s = re.sub(r'([\u4e00-\u9fff])\s+([，。；：、）])', r'\1\2', s)
    s = re.sub(r'([（(，。；：、])\s+([\u4e00-\u9fff])', r'\1\2', s)
    return s.strip()


def _norm_value(val):
    if val is None:
        return ''
    if isinstance(val, float):
        if val != val:  # NaN
            return ''
        if val == int(val):
            return int(val)
        return round(val, 4)
    s = _norm_text(_cell_str(val))
    return s


def _row_has_data(row):
    if not row:
        return False
    for c in row:
        if c is None:
            continue
        if isinstance(c, float) and c != c:
            continue
        if str(c).strip():
            return True
    return False


def _ensure_source(src_path, default_name):
    os.makedirs(_SOURCE_DIR, exist_ok=True)
    dest = os.path.join(_SOURCE_DIR, default_name)
    if os.path.isfile(src_path) and (not os.path.isfile(dest) or os.path.getmtime(src_path) > os.path.getmtime(dest)):
        shutil.copy2(src_path, dest)
    return dest if os.path.isfile(dest) else src_path


def resolve_dataset_id(name, province='吉林'):
    key = (name or '').strip()
    prov = norm_province(province) or '吉林'
    if not _DATASETS:
        rebuild_datasets_registry()
    if key in _DATASETS:
        return key
    batch = BATCH_ALIAS.get(key)
    if batch:
        ds = province_dataset_id(prov, batch)
        if ds in _DATASETS:
            return ds
        if prov == '吉林':
            legacy = legacy_jilin_dataset_id(batch)
            if legacy in _DATASETS:
                return legacy
        return ds
    default = province_dataset_id(prov, 'undergraduate')
    if default in _DATASETS:
        return default
    if 'jilin_2025_expert_undergraduate' in _DATASETS:
        return 'jilin_2025_expert_undergraduate'
    return key or default


def is_expert_dataset(dataset_id):
    dataset_id = resolve_dataset_id(dataset_id)
    meta = _DATASETS.get(dataset_id) or {}
    return meta.get('dataset_type') == 'expert'


def is_strong_base_dataset(dataset_id):
    dataset_id = resolve_dataset_id(dataset_id)
    meta = _DATASETS.get(dataset_id) or {}
    return meta.get('dataset_type') == 'strong_base'


def _expert_batch_bucket(rec_batch):
    batch = str(rec_batch or '')
    if not batch:
        return None
    if '提前批' in batch or batch.startswith('提前') or '提前' in batch:
        return 'early'
    if '专科' in batch or '二段' in batch or '高职' in batch:
        return 'junior'
    if '本科' in batch or '本专科' in batch or '一段' in batch:
        return 'undergraduate'
    if '专项' in batch:
        return 'early'
    return None


STRONG_BATCH_LABEL = '强基计划'
DEFAULT_BATCH_LABELS = {
    'early': '提前批',
    'undergraduate': '本科批',
    'junior': '专科批',
}
PROVINCE_BATCH_ORDER = ('strong', 'early', 'undergraduate', 'junior')


def _looks_like_batch_name(name):
    name = str(name or '').strip()
    if not name or len(name) > 24:
        return False
    if name.endswith('学校') or name.endswith('专科学校'):
        return False
    if '高等专科' in name or '师范高等' in name:
        return False
    keywords = ('批', '提前', '一段', '二段', '段', '本专科', '预科')
    return any(k in name for k in keywords)


def _infer_batch_display_label(records, bucket_key):
    default = DEFAULT_BATCH_LABELS.get(bucket_key, bucket_key)
    counter = Counter()
    for rec in records or []:
        batch = str(rec.get('batch') or '').strip()
        if _looks_like_batch_name(batch):
            counter[batch] += 1
    if not counter:
        return default

    if bucket_key == 'early':
        names = [name for name, _ in counter.most_common(12)]
        if len(names) > 1 and all('提前' in name for name in names):
            if any('专科' in name for name in names) and not any('本科' in name for name in names):
                return '专科提前批'
            return '提前批'
        top = counter.most_common(1)[0][0]
        return top if len(top) <= 14 else '提前批'

    if bucket_key == 'undergraduate':
        names = set(counter.keys())
        if any('一批' in name or '二批' in name for name in names):
            return '本科批'
        if len(names) > 1 and all('本科' in name for name in names):
            return counter.most_common(1)[0][0]
        return counter.most_common(1)[0][0]

    if bucket_key == 'junior':
        top = counter.most_common(1)[0][0]
        return top if _looks_like_batch_name(top) else default

    return default


def _batch_labels_for_province(province):
    manifest = read_manifest(province) or {}
    stored = manifest.get('batch_labels') or {}
    labels = {}
    for batch_key in ('early', 'undergraduate', 'junior'):
        if stored.get(batch_key):
            labels[batch_key] = stored[batch_key]
            continue
        ds_id = resolve_dataset_id(batch_key, province)
        data = _load(ds_id)
        if not data:
            continue
        labels[batch_key] = _infer_batch_display_label(data.get('records') or [], batch_key)
    return labels


def _batch_tab_id(bucket, batch_name, names_in_bucket):
    if len(names_in_bucket) == 1:
        return bucket
    return batch_name


def _batch_tab_sort_key(tab):
    if tab.get('id') == 'strong':
        return (-1, 0, '')
    bucket = tab.get('bucket') or ''
    name = tab.get('batch') or tab.get('label') or ''
    bucket_order = {'early': 0, 'undergraduate': 1, 'junior': 2}.get(bucket, 9)
    if '本科' in name and '专科' not in name:
        sub = 0
    elif '专科' in name:
        sub = 1
    else:
        sub = 2
    return (bucket_order, sub, name)


def _pick_default_batch_tab(tabs):
    expert_tabs = [t for t in tabs if t.get('mode') == 'expert']
    for tab in expert_tabs:
        if tab.get('batch') == '本科批':
            return tab['id']
    for tab in expert_tabs:
        batch_name = tab.get('batch') or ''
        if tab.get('bucket') == 'undergraduate' and '本科' in batch_name and '提前' not in batch_name:
            return tab['id']
    for tab in expert_tabs:
        if tab.get('bucket') == 'undergraduate':
            return tab['id']
    for tab in expert_tabs:
        batch_name = tab.get('batch') or ''
        if '本科' in batch_name and '提前' not in batch_name:
            return tab['id']
    if expert_tabs:
        return expert_tabs[0]['id']
    return tabs[0]['id'] if tabs else 'undergraduate'


def _collect_province_batch_categories(province):
    prov = norm_province(province) or '吉林'
    by_bucket = {}
    for bucket_key in ('early', 'undergraduate', 'junior'):
        ds_id = resolve_dataset_id(bucket_key, prov)
        data = _load(ds_id)
        if not data:
            continue
        counter = Counter()
        for rec in data.get('records') or []:
            batch_name = str(rec.get('batch') or '').strip()
            if _looks_like_batch_name(batch_name):
                counter[batch_name] += 1
        names = [name for name, count in counter.most_common() if count > 0]
        if names:
            by_bucket[bucket_key] = names
    return by_bucket


def list_province_batches(province='吉林'):
    """返回某省可用批次 Tab：每个实际批次类别一个按钮 + 强基计划；默认本科批。"""
    prov = norm_province(province) or '吉林'
    by_bucket = _collect_province_batch_categories(prov)
    tabs = []

    strong_id = resolve_dataset_id('strong', prov)
    strong_meta = _DATASETS.get(strong_id) or {}
    strong = dataset_status(strong_id)
    if strong.get('count', 0) > 0 and strong_meta.get('dataset_type') == 'strong_base':
        tabs.append({
            'id': 'strong',
            'label': STRONG_BATCH_LABEL,
            'count': strong['count'],
            'mode': 'strong',
            'bucket': 'strong',
            'batch': '',
        })

    for bucket_key in ('early', 'undergraduate', 'junior'):
        batch_names = by_bucket.get(bucket_key) or []
        for batch_name in batch_names:
            ds_id = resolve_dataset_id(bucket_key, prov)
            data = _load(ds_id)
            count = sum(
                1 for rec in (data or {}).get('records') or []
                if str(rec.get('batch') or '').strip() == batch_name
            )
            if count <= 0:
                continue
            tabs.append({
                'id': _batch_tab_id(bucket_key, batch_name, batch_names),
                'label': batch_name,
                'count': count,
                'mode': 'expert',
                'bucket': bucket_key,
                'batch': batch_name,
            })

    tabs.sort(key=_batch_tab_sort_key)
    if tabs and tabs[0]['id'] == 'strong' and len(tabs) > 1:
        strong_tab = tabs.pop(0)
        tabs.insert(0, strong_tab)

    default_batch = _pick_default_batch_tab(tabs)
    batch_labels = {tab['id']: tab['label'] for tab in tabs}
    return {
        'province': prov,
        'batches': tabs,
        'default_batch': default_batch,
        'batch_labels': batch_labels,
    }


def _read_sheet_rows(xlsx_path):
    ext = os.path.splitext(xlsx_path)[1].lower()
    if ext == '.xls':
        import pandas as pd
        df = pd.read_excel(xlsx_path, header=None, engine='xlrd')
        return df.values.tolist()
    import openpyxl
    try:
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        ws = wb.active
        rows = [list(row) for row in ws.iter_rows(values_only=True)]
        wb.close()
        return rows
    except Exception:
        import pandas as pd
        try:
            df = pd.read_excel(xlsx_path, header=None, engine='xlrd')
        except Exception:
            df = pd.read_excel(xlsx_path, header=None)
        return df.values.tolist()


def _detect_expert_data_start(rows):
    for i, row in enumerate(rows[:10]):
        cells = [_cell_str(c) for c in (row or [])]
        joined = ' '.join(cells)
        if '院校名称' in joined:
            return i + 1
    return 3


def _register_dataset(ds_id, storage_path, batch_key, dataset_type, province='', year=None, storage='sqlite'):
    fields = STRONG_BASE_FIELDS if dataset_type == 'strong_base' else EXPERT_FIELDS
    _DATASETS[ds_id] = {
        'title': SYSTEM_TITLE,
        'db_path': storage_path if storage == 'sqlite' else '',
        'batch_key': batch_key,
        'json': storage_path,
        'storage': storage,
        'fields': fields,
        'dataset_type': dataset_type,
        'province': province,
        'year': year,
    }


def rebuild_datasets_registry():
    global _DATASETS, EXPERT_DATASET_IDS
    _DATASETS = {}
    expert_ids = set()

    jilin_has_db = province_has_db('吉林')

    legacy_files = {
        'early': EXPERT_EARLY_JSON,
        'undergraduate': EXPERT_UNDERGRADUATE_JSON,
        'junior': EXPERT_JUNIOR_JSON,
        'strong': STRONG_BASE_JSON,
    }
    for batch_key, json_path in legacy_files.items():
        ds_type = 'strong_base' if batch_key == 'strong' else 'expert'
        ds_id = legacy_jilin_dataset_id(batch_key)
        if jilin_has_db and batch_exists('吉林', batch_key):
            _register_dataset(
                ds_id, province_db_for_batch('吉林', batch_key), batch_key, ds_type,
                province='吉林', year=2025,
            )
        elif os.path.isfile(json_path):
            _register_dataset(
                ds_id, json_path, batch_key, ds_type,
                province='吉林', year=2025, storage='json',
            )
        else:
            continue
        if ds_type == 'expert':
            expert_ids.add(ds_id)

    if os.path.isdir(PROVINCES_DIR):
        for row in list_imported_provinces():
            province = row['province']
            manifest = row.get('manifest') or {}
            year = manifest.get('data_year') or DEFAULT_DATA_YEAR
            use_db = province_has_db(province)
            for batch_key in ('early', 'undergraduate', 'junior', 'strong'):
                if use_db:
                    if not batch_exists(province, batch_key):
                        continue
                    storage_path = province_db_for_batch(province, batch_key)
                    storage = 'sqlite'
                else:
                    json_path = province_json_path(province, batch_key)
                    if not os.path.isfile(json_path):
                        continue
                    storage_path = json_path
                    storage = 'json'
                ds_type = 'strong_base' if batch_key == 'strong' else 'expert'
                ds_id = province_dataset_id(province, batch_key, year)
                _register_dataset(
                    ds_id, storage_path, batch_key, ds_type,
                    province=province, year=year, storage=storage,
                )
                if ds_type == 'expert':
                    expert_ids.add(ds_id)
                if province == '吉林':
                    legacy_id = legacy_jilin_dataset_id(batch_key)
                    if legacy_id not in _DATASETS:
                        _register_dataset(
                            legacy_id, storage_path, batch_key, ds_type,
                            province='吉林', year=year, storage=storage,
                        )
                        if ds_type == 'expert':
                            expert_ids.add(legacy_id)

    EXPERT_DATASET_IDS = frozenset(expert_ids)
    _CACHE.clear()
    return _DATASETS


def _write_expert_bucket(bucket_key, records, province='吉林', year=None, json_path=None, ds_id=None):
    year = year or DEFAULT_RECORD_YEAR
    province = norm_province(province) or '吉林'
    if ds_id is None:
        ds_id = province_dataset_id(province, bucket_key, year=DEFAULT_DATA_YEAR)
    batch_label = _infer_batch_display_label(records, bucket_key)
    payload = {
        'id': ds_id,
        'title': SYSTEM_TITLE,
        'dataset_type': 'expert',
        'batch': batch_label,
        'province': province,
        'year': year,
        'count': len(records),
        'columns': [{'key': k, 'label': lb} for k, lb in EXPERT_FIELDS],
        'records': records,
    }
    os.makedirs(province_dir(province), exist_ok=True)
    payload = db_write_expert_bucket(
        province, bucket_key, records, payload, EXPERT_KEYS, STRONG_KEYS,
    )
    _CACHE.pop(ds_id, None)
    return payload


def build_expert_json(xlsx_path=None, json_path=None, province='吉林'):
    return build_expert_json_for_province(province, xlsx_path=xlsx_path, legacy_json_path=json_path)


def build_expert_json_for_province(province, xlsx_path=None, copy_source=False, legacy_json_path=None):
    province = norm_province(province) or '吉林'
    if copy_source and xlsx_path:
        copy_province_sources(province, expert_path=xlsx_path)
    if not xlsx_path:
        for candidate in (
            os.path.join(province_source_dir(province), 'expert.xlsx'),
            os.path.join(province_source_dir(province), 'expert.xls'),
            _DEFAULT_EXPERT_XLSX if province == '吉林' else '',
        ):
            if candidate and os.path.isfile(candidate):
                xlsx_path = candidate
                break
    if not xlsx_path or not os.path.isfile(xlsx_path):
        raise FileNotFoundError(xlsx_path or province)

    from gaokao_expert_import import parse_expert_sheet_rows

    rows = _read_sheet_rows(xlsx_path)
    all_records, import_meta = parse_expert_sheet_rows(rows, province=province)
    if import_meta.get('error'):
        raise ValueError(f'{province} 专家版表头无法识别: {import_meta.get("error")}')

    buckets = {key: [] for key in EXPERT_BATCH_BUCKETS}
    for rec in all_records:
        bucket = _expert_batch_bucket(rec.get('batch'))
        if bucket:
            buckets[bucket].append(rec)

    results = {}
    counts = {}
    batch_labels = {}
    for bucket_key in EXPERT_BATCH_BUCKETS:
        payload = _write_expert_bucket(
            bucket_key,
            buckets[bucket_key],
            province=province,
            year=DEFAULT_RECORD_YEAR,
        )
        results[bucket_key] = payload
        counts[bucket_key] = payload['count']
        if payload['count']:
            batch_labels[bucket_key] = payload['batch']

    combined = []
    for bucket_key in ('early', 'undergraduate', 'junior'):
        combined.extend(buckets[bucket_key])
    legacy_path = legacy_json_path
    if legacy_path is None and province == '吉林':
        legacy_path = EXPERT_JSON
    if legacy_path:
        legacy_payload = {
            'id': f'{province_slug(province)}_{DEFAULT_DATA_YEAR}_expert',
            'title': SYSTEM_TITLE,
            'dataset_type': 'expert',
            'province': province,
            'year': DEFAULT_RECORD_YEAR,
            'count': len(combined),
            'columns': [{'key': k, 'label': lb} for k, lb in EXPERT_FIELDS],
            'records': combined,
        }
        os.makedirs(os.path.dirname(legacy_path), exist_ok=True)
        save_json_dataset(legacy_path, legacy_payload)

    existing = read_manifest(province) or {}
    write_manifest(province, {
        'data_year': DEFAULT_DATA_YEAR,
        'record_year': DEFAULT_RECORD_YEAR,
        'expert_source': os.path.basename(xlsx_path),
        'strong_source': existing.get('strong_source', ''),
        'counts': {**{k: v for k, v in (existing.get('counts') or {}).items() if k == 'strong'}, **counts},
        'batch_labels': {
            **(existing.get('batch_labels') or {}),
            **batch_labels,
        },
        'expert_import': {
            'template': import_meta.get('template'),
            'header_row': import_meta.get('header_row'),
            'column_count': import_meta.get('column_count'),
            'mapped_fields': import_meta.get('mapped_fields'),
            'has_plan_category': 'plan_category' in (import_meta.get('column_map') or {}),
        },
        'imported_at': datetime.now().isoformat(timespec='seconds'),
    })
    rebuild_datasets_registry()
    return {'undergraduate': results['undergraduate'], 'counts': counts}


def split_expert_json_from_legacy(json_path=None):
    """将旧版合并 JSON 拆成提前批 / 本科批 / 专科批三份。"""
    json_path = json_path or EXPERT_JSON
    if not os.path.isfile(json_path):
        raise FileNotFoundError(json_path)
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    buckets = {key: [] for key in EXPERT_BATCH_BUCKETS}
    for rec in data.get('records') or []:
        bucket = _expert_batch_bucket(rec.get('batch'))
        if bucket:
            buckets[bucket].append(rec)
    results = {}
    for bucket_key in EXPERT_BATCH_BUCKETS:
        results[bucket_key] = _write_expert_bucket(
            bucket_key,
            buckets[bucket_key],
            province='吉林',
            year=DEFAULT_RECORD_YEAR,
            json_path=EXPERT_BATCH_BUCKETS[bucket_key]['json'],
            ds_id=EXPERT_BATCH_BUCKETS[bucket_key]['id'],
        )
    return results


def build_strong_base_json(xlsx_path=None, json_path=None, province='吉林'):
    return build_strong_base_json_for_province(province, xlsx_path=xlsx_path)


def build_strong_base_json_for_province(province, xlsx_path=None, copy_source=False):
    province = norm_province(province) or '吉林'
    if copy_source and xlsx_path:
        copy_province_sources(province, strong_path=xlsx_path)
    if not xlsx_path:
        for candidate in (
            os.path.join(province_source_dir(province), 'strong_base.xlsx'),
            os.path.join(province_source_dir(province), 'strong_base.xls'),
            _DEFAULT_STRONG_XLSX if province == '吉林' else '',
        ):
            if candidate and os.path.isfile(candidate):
                xlsx_path = candidate
                break
    if not xlsx_path or not os.path.isfile(xlsx_path):
        raise FileNotFoundError(xlsx_path or province)

    rows = _read_sheet_rows(xlsx_path)
    records = []
    start = 2
    for i, row in enumerate(rows, start=1):
        if i <= start:
            continue
        if not _row_has_data(row):
            continue
        cells = list(row)
        rec = {}
        for idx, (key, _label) in enumerate(STRONG_BASE_FIELDS):
            val = cells[idx] if idx < len(cells) else None
            rec[key] = _norm_value(val)
        if not rec.get('school_name'):
            continue
        if not rec.get('province'):
            rec['province'] = province
        records.append(rec)

    json_path = province_json_path(province, 'strong')
    ds_id = province_dataset_id(province, 'strong')
    payload = {
        'id': ds_id,
        'title': SYSTEM_TITLE,
        'dataset_type': 'strong_base',
        'province': province,
        'year': DEFAULT_RECORD_YEAR,
        'count': len(records),
        'columns': [{'key': k, 'label': lb} for k, lb in STRONG_BASE_FIELDS],
        'records': records,
    }
    os.makedirs(province_dir(province), exist_ok=True)
    db_write_strong_base(province, records, payload, STRONG_KEYS, EXPERT_KEYS)
    _CACHE.pop(ds_id, None)

    manifest = read_manifest(province) or {}
    counts = dict(manifest.get('counts') or {})
    counts['strong'] = len(records)
    batch_labels = dict(manifest.get('batch_labels') or {})
    if len(records):
        batch_labels['strong'] = STRONG_BATCH_LABEL
    write_manifest(province, {
        'data_year': manifest.get('data_year', DEFAULT_DATA_YEAR),
        'record_year': manifest.get('record_year', DEFAULT_RECORD_YEAR),
        'expert_source': manifest.get('expert_source', ''),
        'strong_source': os.path.basename(xlsx_path),
        'counts': counts,
        'batch_labels': batch_labels,
        'imported_at': datetime.now().isoformat(timespec='seconds'),
    })
    rebuild_datasets_registry()
    return payload


def _load_dataset_meta(meta):
    if meta.get('storage') == 'sqlite' or (
        meta.get('db_path') and os.path.isfile(meta.get('db_path') or '')
    ):
        return read_dataset_by_path(
            meta['db_path'],
            meta.get('batch_key') or 'undergraduate',
            meta.get('dataset_type') or 'expert',
            EXPERT_KEYS,
            STRONG_KEYS,
        )
    if meta.get('json') and os.path.isfile(meta['json']) and meta['json'].endswith('.json'):
        from gaokao_json_parts import load_json_dataset
        return load_json_dataset(meta['json'])
    return None


def _load(dataset_id):
    if dataset_id in _CACHE:
        return _CACHE[dataset_id]
    meta = _DATASETS.get(dataset_id)
    if not meta:
        _CACHE[dataset_id] = None
        return None
    has_sqlite = meta.get('storage') == 'sqlite' and meta.get('db_path') and os.path.isfile(meta['db_path'])
    has_json = meta.get('json') and os.path.isfile(meta['json']) and str(meta.get('json', '')).endswith('.json')
    if not has_sqlite and not has_json:
        _CACHE[dataset_id] = None
        return None
    data = _load_dataset_meta(meta)
    if data is None:
        _CACHE[dataset_id] = None
        return None
    if meta.get('dataset_type') == 'expert':
        data = dict(data)
        data['records'] = [_normalize_expert_record(r) for r in data.get('records') or []]
    _CACHE[dataset_id] = data
    return data


def dataset_status(dataset_id):
    meta = _DATASETS.get(dataset_id)
    if not meta:
        return {'available': False, 'count': 0}
    if meta.get('storage') == 'sqlite' and meta.get('batch_key') and meta.get('province'):
        count = db_dataset_count(meta['province'], meta['batch_key'])
    elif meta.get('json') and os.path.isfile(meta['json']):
        from gaokao_json_parts import dataset_file_count
        count = dataset_file_count(meta['json'])
    else:
        count = 0
    return {
        'available': count > 0,
        'count': count,
        'title': meta['title'],
        'id': dataset_id,
    }


def sync_jilin_legacy_json(province='吉林'):
    province = norm_province(province)
    if province != '吉林':
        return
    mapping = (
        (EXPERT_EARLY_JSON, 'early'),
        (EXPERT_UNDERGRADUATE_JSON, 'undergraduate'),
        (EXPERT_JUNIOR_JSON, 'junior'),
        (STRONG_BASE_JSON, 'strong'),
    )
    for dest, batch_key in mapping:
        db_path = province_db_for_batch('吉林', batch_key)
        if not os.path.isfile(db_path) or not batch_exists('吉林', batch_key):
            continue
        data = read_dataset('吉林', batch_key, EXPERT_KEYS, STRONG_KEYS)
        if not data:
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        save_json_dataset(dest, data)


def _expert_dataset_ids_for_province(province):
    prov = norm_province(province) or '吉林'
    ids = []
    for batch in ('undergraduate', 'early', 'junior'):
        ds = province_dataset_id(prov, batch, DEFAULT_DATA_YEAR)
        if ds in _DATASETS:
            ids.append(ds)
        legacy = legacy_jilin_dataset_id(batch)
        if prov == '吉林' and legacy in _DATASETS and legacy not in ids:
            ids.append(legacy)
    return ids


def system_status(province='吉林'):
    prov = norm_province(province) or '吉林'
    early = dataset_status(resolve_dataset_id('early', prov))
    undergrad = dataset_status(resolve_dataset_id('undergraduate', prov))
    junior = dataset_status(resolve_dataset_id('junior', prov))
    strong = dataset_status(resolve_dataset_id('strong', prov))
    expert_count = (
        (early.get('count') or 0)
        + (undergrad.get('count') or 0)
        + (junior.get('count') or 0)
    )
    return {
        'title': SYSTEM_TITLE,
        'available': expert_count > 0 or strong.get('available'),
        'expert_count': expert_count,
        'expert_early_count': early.get('count') or 0,
        'expert_undergraduate_count': undergrad.get('count') or 0,
        'expert_junior_count': junior.get('count') or 0,
        'strong_base_count': strong.get('count') or 0,
        'total_count': expert_count + (strong.get('count') or 0),
    }


def list_datasets():
    return [dataset_status(k) for k in _DATASETS]


def list_schools(dataset_id, query='', limit=60, provinces=''):
    data = _load(dataset_id)
    if not data:
        return {'ok': False, 'schools': []}
    q = (query or '').strip().lower()
    province_set = {_norm_province(p) for p in _parse_csv_param(provinces) if _norm_province(p)}
    from school_reference_loader import lookup_school_profile

    seen = set()
    schools = []
    code_by_name = {}
    prov_by_name = {}
    for rec in data.get('records') or []:
        name = str(rec.get('school_name') or '').strip()
        if not name:
            continue
        if name not in code_by_name and rec.get('school_code'):
            code_by_name[name] = str(rec.get('school_code') or '').strip()
        if name not in prov_by_name:
            prov = _resolve_school_province(rec)
            if prov:
                prov_by_name[name] = prov
        if name in seen:
            continue
        if q and q not in name.lower():
            continue
        seen.add(name)
        prov = prov_by_name.get(name, '')
        in_region = bool(province_set and prov in province_set) if province_set else False
        schools.append({
            'school_name': name,
            'province': prov,
            'school_code': code_by_name.get(name, ''),
            'in_selected_region': in_region,
        })
        if len(schools) >= limit:
            break
    schools.sort(key=lambda s: s.get('school_name') or '')
    return {'ok': True, 'schools': schools}


YEAR_KEYS = [
    {'year': 23, 'score_min': 'm2023_min_score', 'score_max': None, 'rank_min': 'm2023_min_rank', 'rank_max': None},
    {'year': 24, 'score_min': 'm2024_min_score', 'score_max': None, 'rank_min': 'm2024_min_rank', 'rank_max': None},
    {'year': 25, 'score_min': 'm2025_min_score', 'score_max': 'm2025_max_score', 'rank_min': 'm2025_min_rank', 'rank_max': 'm2025_max_rank'},
]


def _parse_num(val):
    if val is None or val == '':
        return None
    if isinstance(val, (int, float)):
        return int(val) if isinstance(val, float) and val == int(val) else val
    try:
        s = str(val).replace(',', '').strip()
        if not s:
            return None
        n = float(s)
        return int(n) if n == int(n) else n
    except (TypeError, ValueError):
        return None


def _pair_min_max(a, b):
    if a is None and b is None:
        return None, None
    if a is None:
        return b, b
    if b is None:
        return a, a
    return min(a, b), max(a, b)


def _year_series(rec, kind):
    series = []
    for yk in YEAR_KEYS:
        min_key = yk['score_min'] if kind == 'score' else yk['rank_min']
        max_key = yk['score_max'] if kind == 'score' else yk['rank_max']
        vmin = _parse_num(rec.get(min_key))
        vmax = _parse_num(rec.get(max_key)) if max_key else None
        if vmin is not None and vmax is not None:
            lo, hi = _pair_min_max(vmin, vmax)
        elif vmin is not None:
            # 仅有最低分/最低位次：分数放 min，位次放 max（位次数值越大越靠后）
            lo, hi = (vmin, None) if kind == 'score' else (None, vmin)
        elif vmax is not None:
            lo, hi = (None, vmax) if kind == 'score' else (vmax, None)
        else:
            lo, hi = None, None
        series.append({
            'year': yk['year'],
            'min': lo,
            'max': hi,
            'has_data': lo is not None or hi is not None,
        })
    return series


YEAR_PROB_WEIGHTS = {
    25: 0.45,
    24: 0.35,
    23: 0.20,
}


def _year_rank_band(rec, yk):
    """返回某年录取位次区间 (best, worst)，数值越小表示排名越靠前。"""
    vmin = _parse_num(rec.get(yk['rank_min']))
    vmax = _parse_num(rec.get(yk['rank_max'])) if yk['rank_max'] else None
    if vmin is None and vmax is None:
        return None, None
    if vmin is not None and vmax is not None:
        return _pair_min_max(vmin, vmax)
    if vmin is not None:
        return None, vmin
    return vmax, None


def _year_rank_prob(user_rank, best, worst):
    """
    单年录取概率：user_rank 与当年最好/最差录取位次比较。
    best：当年最好录取位次（数值最小）；worst：当年最差录取位次（数值最大）。
    """
    if best is None and worst is None:
        return None
    if best is None:
        best = worst
    if worst is None:
        worst = best
    if best > worst:
        best, worst = worst, best

    if user_rank <= best:
        cushion = (best - user_rank) / max(best, 1)
        return min(0.97, 0.90 + cushion * 0.07)

    if user_rank >= worst:
        if user_rank >= worst * 1.2:
            tail = (user_rank - worst * 1.2) / max(user_rank, 1)
            return max(0.03, 0.10 - tail * 0.07)
        overshoot = (user_rank - worst) / max(worst, 1)
        return max(0.12, 0.42 - overshoot * 0.30)

    span = worst - best
    if span <= 0:
        return 0.55
    ratio = (user_rank - best) / span
    return 0.86 - ratio * 0.38


def calc_probability(user_rank, rec):
    """
    根据考生位次与过去三年专业录取位次估算概率。
    按年分别计算后加权：2025 年 45%、2024 年 35%、2023 年 20%（缺失年份自动归一化）。
    每年以「最好录取位次～最差录取位次」为参考区间，位次优于最好为保，劣于最差为冲。
    """
    if user_rank is None:
        return None

    weighted_sum = 0.0
    weight_total = 0.0
    for yk in YEAR_KEYS:
        year = yk['year']
        best, worst = _year_rank_band(rec, yk)
        if best is None and worst is None:
            continue
        year_prob = _year_rank_prob(user_rank, best, worst)
        if year_prob is None:
            continue
        w = YEAR_PROB_WEIGHTS.get(year, 0.2)
        weighted_sum += year_prob * w
        weight_total += w

    if weight_total <= 0:
        return None

    return round(max(0.03, min(0.97, weighted_sum / weight_total)), 2)


def _primary_min_rank(rec):
    """最近一年可用的专业最低位次（数值越小越靠前）。"""
    for key in ('m2025_min_rank', 'm2024_min_rank', 'm2023_min_rank'):
        v = _parse_num(rec.get(key))
        if v is not None:
            return v
    return None


def _primary_min_score(rec):
    """最近一年可用的专业最低分（用于无概率时按分数排序）。"""
    for key in ('m2025_min_score', 'm2024_min_score', 'm2023_min_score'):
        v = _parse_num(rec.get(key))
        if v is not None:
            return v
    return None


def _expert_sort_key(rec, user_rank=None):
    prob = calc_probability(user_rank, rec)
    score = _primary_min_score(rec)
    score_key = -(score if score is not None else float('inf'))
    if prob is not None:
        return (0, prob, score_key)
    return (1, score_key, _primary_min_rank(rec) or float('inf'))


def format_expert_view(rec, user_rank=None, user_score=None):
    """普通高考列表页展示字段（概率与折线图数据由服务端计算）。"""
    return {
        'probability': calc_probability(user_rank, rec),
        'school_name': rec.get('school_name') or '',
        'major_name': rec.get('major_name') or '',
        'duration': rec.get('duration') or '',
        'tuition': rec.get('tuition') or '',
        'plan_count': rec.get('plan_count') or '',
        'school_type': rec.get('school_type') or '',
        'score_chart': {
            'series': _year_series(rec, 'score'),
            'current': user_score,
        },
        'rank_chart': {
            'series': _year_series(rec, 'rank'),
            'current': user_rank,
        },
    }


def _batch_matches(rec_batch, batch_q):
    rec_batch = str(rec_batch or '')
    if not batch_q:
        return True
    if batch_q == '提前批':
        return '提前批' in rec_batch
    return rec_batch == batch_q


def _norm_province(name):
    s = str(name or '').strip()
    for suffix in ('维吾尔自治区', '回族自治区', '壮族自治区', '自治区', '省', '市'):
        s = s.replace(suffix, '')
    return s


_KNOWN_PROVINCES = frozenset(_norm_province(p) for p in PROVINCE_LIST)


def _is_numeric_junk(val):
    s = str(val or '').strip()
    if not s:
        return False
    if s.isdigit():
        return True
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _is_known_province_name(val):
    return _norm_province(val) in _KNOWN_PROVINCES


def _normalize_expert_record(rec):
    """修正部分省份 Excel 列错位：院校名/所在省。"""
    if not isinstance(rec, dict):
        return rec
    rec = dict(rec)
    name = str(rec.get('school_name') or '').strip()
    group_code = str(rec.get('major_group_code') or '').strip()
    if name.isdigit() and group_code and not group_code.isdigit():
        if not str(rec.get('school_code') or '').strip():
            rec['school_code'] = name
        rec['school_name'] = group_code

    prov = str(rec.get('school_province') or '').strip()
    if not prov or _is_numeric_junk(prov) or not _is_known_province_name(prov):
        aff = str(rec.get('affiliation') or '').strip()
        if aff and _is_known_province_name(aff):
            rec['school_province'] = aff
        elif _is_numeric_junk(prov):
            rec['school_province'] = ''
    return rec


def _resolve_school_name(rec):
    return str((rec or {}).get('school_name') or '').strip()


def _resolve_school_province(rec):
    from school_reference_loader import lookup_school_profile

    name = _resolve_school_name(rec)
    if name:
        profile = lookup_school_profile(name) or {}
        prov = _norm_province(profile.get('province') or '')
        if prov and _is_known_province_name(prov):
            return prov
    raw = str((rec or {}).get('school_province') or '').strip()
    if raw and not _is_numeric_junk(raw):
        prov = _norm_province(raw)
        if _is_known_province_name(prov):
            return prov
    aff = str((rec or {}).get('affiliation') or '').strip()
    if aff and _is_known_province_name(aff):
        return _norm_province(aff)
    return ''


def _parse_csv_param(raw):
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        parts = raw
    else:
        parts = str(raw).split(',')
    out = []
    seen = set()
    for part in parts:
        val = str(part).strip()
        if not val or val in seen:
            continue
        seen.add(val)
        out.append(val)
    return out


def _record_matches_major_filter(rec, category_titles, major_names):
    if not category_titles and not major_names:
        return True
    mc = str(rec.get('major_category') or '').strip()
    mn = str(rec.get('major_name') or '').strip()
    mfull = str(rec.get('major_full_name') or '').strip()
    if mc and mc in category_titles:
        return True
    if mn and mn in major_names:
        return True
    if mfull and mfull in major_names:
        return True
    for title in category_titles:
        if not title:
            continue
        if title in mc or mc in title:
            return True
        if title in mn or title in mfull:
            return True
    return False


def _record_matches_province_filter(rec, province_codes):
    if not province_codes:
        return True
    school_prov = _resolve_school_province(rec)
    return school_prov in province_codes


def _score_desc_sort_key(rec):
    score = _primary_min_score(rec)
    if score is None:
        return (1, 0)
    return (0, -score)


def _score_desc_sort_key(rec):
    score = _primary_min_score(rec)
    if score is None:
        return (1, 0)
    return (0, -score)


def _prepare_search_filters(school='', major='', batch='', category='', school_type='',
                            provinces='', major_categories='', major_groups=''):
    school_q = (school or '').strip().lower()
    major_q = (major or '').strip().lower()
    batch_q = (batch or '').strip()
    cat_q = (category or '').strip()
    type_q = (school_type or '').strip()
    province_list = [_norm_province(p) for p in _parse_csv_param(provinces)]
    province_set = {p for p in province_list if p}
    major_cat_titles = _parse_csv_param(major_categories)
    major_group_ids = _parse_csv_param(major_groups)
    profile_filter = bool(province_set or major_cat_titles or major_group_ids)
    category_titles = set()
    major_name_set = set()
    if major_cat_titles or major_group_ids:
        from major_catalog import build_category_major_filter
        category_titles, major_name_set = build_category_major_filter(
            major_cat_titles, major_group_ids,
        )
    return {
        'school_q': school_q,
        'major_q': major_q,
        'batch_q': batch_q,
        'cat_q': cat_q,
        'type_q': type_q,
        'province_set': province_set,
        'category_titles': category_titles,
        'major_name_set': major_name_set,
        'profile_filter': profile_filter,
    }


def _record_passes_filters(rec, filters, dataset_id, skip_major_filter=False, extra_school_set=None):
    school_name = str(rec.get('school_name') or '').strip()
    is_extra = bool(extra_school_set and school_name in extra_school_set)
    if filters['school_q'] and filters['school_q'] not in school_name.lower():
        return False
    if filters['batch_q'] and not _batch_matches(rec.get('batch'), filters['batch_q']):
        return False
    if filters['cat_q'] and str(rec.get('category') or '') != filters['cat_q']:
        return False
    if filters['type_q'] and str(rec.get('school_type') or '') != filters['type_q']:
        return False
    if filters['province_set'] and not _record_matches_province_filter(rec, filters['province_set']):
        if not is_extra and not is_strong_base_dataset(dataset_id):
            return False
    if not skip_major_filter:
        if filters['category_titles'] or filters['major_name_set']:
            if not _record_matches_major_filter(rec, filters['category_titles'], filters['major_name_set']):
                return False
    if filters['major_q']:
        blob = ' '.join([
            str(rec.get('major_name') or ''),
            str(rec.get('major_full_name') or ''),
            str(rec.get('major_note') or ''),
            str(rec.get('major_code') or ''),
        ]).lower()
        if filters['major_q'] not in blob:
            return False
    return True


def _probability_tier(prob):
    if prob is None:
        return '', 'none'
    if prob >= 0.8:
        return '保', 'safe'
    if prob >= 0.5:
        return '稳', 'steady'
    return '冲', 'reach'


def _format_major_detail(rec, user_rank=None, user_score=None):
    prob = calc_probability(user_rank, rec)
    tier_label, tier_class = _probability_tier(prob)
    return {
        'major_name': rec.get('major_name') or '',
        'major_code': rec.get('major_code') or '',
        'major_full_name': rec.get('major_full_name') or '',
        'major_note': rec.get('major_note') or '',
        'subject_requirement': rec.get('subject_requirement') or '',
        'duration': rec.get('duration') or '',
        'tuition': rec.get('tuition') or '',
        'plan_count': rec.get('plan_count') or '',
        'major_category': rec.get('major_category') or '',
        'is_new': rec.get('is_new') or '',
        'probability': prob,
        'tier_label': tier_label,
        'tier_class': tier_class,
        'score_2025': rec.get('m2025_min_score') or '',
        'score_max_2025': rec.get('m2025_max_score') or '',
        'rank_2025': rec.get('m2025_min_rank') or '',
        'rank_max_2025': rec.get('m2025_max_rank') or '',
        'score_2024': rec.get('m2024_min_score') or '',
        'rank_2024': rec.get('m2024_min_rank') or '',
        'score_2023': rec.get('m2023_min_score') or '',
        'rank_2023': rec.get('m2023_min_rank') or '',
        'score_chart': {
            'series': _year_series(rec, 'score'),
            'current': user_score,
        },
        'rank_chart': {
            'series': _year_series(rec, 'rank'),
            'current': user_rank,
        },
    }


def _build_major_groups(records, user_rank=None, user_score=None):
    buckets = {}
    for rec in records:
        code = str(rec.get('major_group_code') or rec.get('group_code') or '').strip()
        name = str(rec.get('major_group_name') or '').strip()
        key = code or name or str(rec.get('major_name') or '').strip()
        if not key:
            continue
        if key not in buckets:
            buckets[key] = {
                'group_code': code or key,
                'group_name': name,
                'records': [],
            }
        buckets[key]['records'].append(rec)

    groups = []
    for bucket in buckets.values():
        majors = []
        plan_total = 0
        best_prob = None
        for rec in bucket['records']:
            prob = calc_probability(user_rank, rec)
            pc = _parse_num(rec.get('plan_count'))
            if pc:
                plan_total += int(pc)
            if prob is not None and (best_prob is None or prob > best_prob):
                best_prob = prob
            detail = _format_major_detail(rec, user_rank, user_score)
            majors.append({
                'major_name': detail['major_name'],
                'probability': prob,
                'plan_count': detail['plan_count'],
                'tier_label': detail['tier_label'],
                'tier_class': detail['tier_class'],
                'detail': detail,
            })
        majors.sort(key=lambda m: (-(m['probability'] or 0), str(m['major_name'])))
        g_tier_label, g_tier_class = _probability_tier(best_prob)
        groups.append({
            'group_code': bucket['group_code'],
            'group_name': bucket['group_name'],
            'plan_count': plan_total,
            'probability': best_prob,
            'tier_label': g_tier_label,
            'tier_class': g_tier_class,
            'majors': majors,
        })

    groups.sort(key=lambda g: (-(g.get('probability') or 0), str(g.get('group_code') or '')))
    return groups


def _format_school_card(school_name, records, user_rank=None, user_score=None, cat_q='', all_records=None):
    from school_reference_loader import lookup_school_profile

    profile = lookup_school_profile(school_name) or {}
    sample = records[0]
    group_keys = set()
    plan_total = 0
    best_prob = None
    best_score = None
    best_rank = None

    for rec in records:
        group_key = '||'.join([
            str(rec.get('major_group_code') or rec.get('group_code') or '').strip(),
            str(rec.get('major_group_name') or '').strip(),
        ]).strip('|')
        if group_key:
            group_keys.add(group_key)
        pc = _parse_num(rec.get('plan_count'))
        if pc:
            plan_total += int(pc)
        prob = calc_probability(user_rank, rec)
        if prob is not None and (best_prob is None or prob > best_prob):
            best_prob = prob
        score = _primary_min_score(rec)
        if score is not None and (best_score is None or score > best_score):
            best_score = score
            best_rank = _primary_min_rank(rec)

    tier_label, tier_class = _probability_tier(best_prob)
    province = profile.get('province') or str(sample.get('school_province') or '')
    nature = profile.get('nature') or str(sample.get('ownership') or '')
    subject = profile.get('subject') or str(sample.get('school_edu_level') or '') or '本科'
    location_parts = [p for p in [province, nature, subject] if p]
    location_line = ' · '.join(location_parts)

    tags = []
    for lb in profile.get('label') or []:
        lb = str(lb or '').strip()
        if lb and '/' not in lb and lb not in tags:
            tags.append(lb)
    affiliation = str(sample.get('affiliation') or '').strip()
    if affiliation and '/' not in affiliation and affiliation not in tags:
        tags.insert(0, affiliation)
    for part in re.split(r'[,，、\s]+', str(sample.get('school_tags') or '')):
        part = part.strip()
        if part and '/' not in part and part not in tags and len(tags) < 10:
            tags.append(part)

    major_groups = _build_major_groups(records, user_rank, user_score)
    if all_records is not None:
        all_group_map = {
            g['group_code']: g
            for g in _build_major_groups(all_records, user_rank, user_score)
        }
        for group in major_groups:
            full_group = all_group_map.get(group['group_code'])
            group['all_majors'] = (full_group or group)['majors']
        all_major_groups = _build_major_groups(all_records, user_rank, user_score)
    else:
        for group in major_groups:
            group['all_majors'] = group['majors']
        all_major_groups = _build_major_groups(records, user_rank, user_score)
    for group in all_major_groups:
        group['all_majors'] = group['majors']
    major_group_count = len(major_groups)
    category_label = cat_q or str(sample.get('category') or '物理')

    return {
        'school_name': school_name,
        'school_code': str(sample.get('school_code') or ''),
        'probability': best_prob,
        'tier_label': tier_label,
        'tier_class': tier_class,
        'location_line': location_line,
        'tags': tags[:10],
        'plan_count': plan_total,
        'min_score': best_score,
        'min_rank': best_rank,
        'category_label': category_label,
        'major_group_count': major_group_count,
        'major_count': len(records),
        'major_groups': major_groups,
        'all_major_groups': all_major_groups,
    }


def _school_card_sort_key(card):
    score = card.get('min_score')
    if score is None:
        return (1, 0)
    return (0, -score)


def _parse_score_num(val):
    if val is None or val == '':
        return None
    try:
        return float(str(val).strip())
    except (TypeError, ValueError):
        return None


def _is_gaokao_like_score(score):
    return score is not None and 400 <= score <= 750


def _strong_reference_score(qualify_score, admit_score):
    q = _parse_score_num(qualify_score)
    a = _parse_score_num(admit_score)
    if _is_gaokao_like_score(q):
        return q
    if _is_gaokao_like_score(a):
        return a
    return None


def _strong_score_status(user_score, qualify_score, admit_score):
    user = _parse_score_num(user_score)
    ref = _strong_reference_score(qualify_score, admit_score)
    if user is None or ref is None:
        return '', 'none'
    if user >= ref:
        return '达标', 'safe'
    if user >= ref - 15:
        return '接近', 'steady'
    return '偏低', 'reach'


def _format_strong_major(rec, user_score=None):
    qualify = rec.get('qualify_score') or ''
    admit = rec.get('admit_score') or ''
    status_label, status_class = _strong_score_status(user_score, qualify, admit)
    user = _parse_score_num(user_score)
    ref = _strong_reference_score(qualify, admit)
    diff = None
    if user is not None and ref is not None:
        diff = round(user - ref, 1)
    return {
        'major_name': rec.get('major_name') or '',
        'province': rec.get('province') or '',
        'qualify_score': qualify,
        'admit_score': admit,
        'score_status_label': status_label,
        'score_status_class': status_class,
        'score_diff': diff,
    }


def _format_strong_school_card(school_name, records, user_score=None):
    from school_reference_loader import lookup_school_profile

    profile = lookup_school_profile(school_name) or {}
    sample = records[0] if records else {}
    majors = [_format_strong_major(rec, user_score) for rec in records]
    tier_priority = {'safe': 0, 'steady': 1, 'reach': 2, 'none': 3}
    majors.sort(key=lambda m: (
        tier_priority.get(m.get('score_status_class') or 'none', 3),
        -(_parse_score_num(m.get('qualify_score')) or 0),
        str(m.get('major_name') or ''),
    ))

    best = majors[0] if majors else {}
    best_label = best.get('score_status_label') or ''
    best_class = best.get('score_status_class') or 'none'
    if not best_label:
        best_label = str(len(majors)) if majors else ''
        best_class = 'none'

    province = profile.get('province') or str(sample.get('province') or '')
    nature = profile.get('nature') or ''
    subject = profile.get('subject') or '本科'
    location_parts = [p for p in [province, nature, subject] if p]
    location_line = ' · '.join(location_parts)

    tags = []
    for lb in profile.get('label') or []:
        lb = str(lb or '').strip()
        if lb and '/' not in lb and lb not in tags:
            tags.append(lb)
    for part in re.split(r'[,，、\s]+', str(profile.get('school_tags') or '')):
        part = part.strip()
        if part and '/' not in part and part not in tags and len(tags) < 8:
            tags.append(part)

    gaokao_refs = [
        _strong_reference_score(m.get('qualify_score'), m.get('admit_score'))
        for m in majors
    ]
    gaokao_refs = [s for s in gaokao_refs if s is not None]
    qualify_range = ''
    if gaokao_refs:
        qualify_range = str(int(min(gaokao_refs))) + '–' + str(int(max(gaokao_refs)))

    return {
        'card_type': 'strong_base',
        'school_name': school_name,
        'location_line': location_line,
        'tags': tags[:8],
        'major_count': len(majors),
        'tier_label': best_label,
        'tier_class': best_class,
        'qualify_range': qualify_range,
        'majors': majors,
    }


def _strong_school_card_sort_key(card):
    tier_order = {'safe': 0, 'steady': 1, 'reach': 2, 'none': 3}
    return (
        tier_order.get(card.get('tier_class') or 'none', 3),
        str(card.get('school_name') or ''),
    )


def search_strong_school_cards(dataset_id, school='', major='', user_score=None, limit=500):
    dataset_id = resolve_dataset_id(dataset_id)
    data = _load(dataset_id)
    if not data:
        return {'ok': False, 'message': '数据不存在', 'records': [], 'total': 0}

    filters = _prepare_search_filters(
        school, major, '', '', '', '', '', '',
    )
    buckets = {}
    for rec in data.get('records') or []:
        if not _record_passes_filters(rec, filters, dataset_id):
            continue
        name = str(rec.get('school_name') or '').strip()
        if not name:
            continue
        buckets.setdefault(name, []).append(rec)

    cards = [
        _format_strong_school_card(name, recs, user_score)
        for name, recs in buckets.items()
    ]
    cards.sort(key=_strong_school_card_sort_key)
    total = len(cards)
    return {
        'ok': True,
        'total': total,
        'records': cards[:limit],
        'view': 'school',
        'dataset_type': 'strong_base',
        'title': data.get('title'),
    }


def search_school_cards(dataset_id, school='', major='', batch='', category='',
                        school_type='', provinces='', major_categories='',
                        major_groups='', user_rank=None, user_score=None,
                        limit=100, sort_by_score=False, extra_schools=''):
    data = _load(dataset_id)
    if not data or not is_expert_dataset(dataset_id):
        return {'ok': False, 'message': '数据不存在', 'records': [], 'total': 0}

    filters = _prepare_search_filters(
        school, major, batch, category, school_type,
        provinces, major_categories, major_groups,
    )
    extra_school_set = set(_parse_csv_param(extra_schools))
    split_expert = is_expert_dataset(dataset_id)
    if not any([
        filters['school_q'], filters['major_q'], filters['batch_q'],
        filters['cat_q'], filters['type_q'], filters['profile_filter'],
        extra_school_set,
    ]) and not split_expert:
        return {'ok': True, 'total': 0, 'records': [], 'view': 'school'}

    grouped = {}
    grouped_all = {}
    for rec in data.get('records') or []:
        if not _record_passes_filters(
            rec, filters, dataset_id, skip_major_filter=True, extra_school_set=extra_school_set,
        ):
            continue
        name = _resolve_school_name(rec)
        if not name:
            continue
        grouped_all.setdefault(name, []).append(rec)
        if not _record_passes_filters(
            rec, filters, dataset_id, extra_school_set=extra_school_set,
        ):
            continue
        grouped.setdefault(name, []).append(rec)

    cards = []
    for name, recs in grouped.items():
        if sort_by_score or filters['profile_filter']:
            recs.sort(key=_score_desc_sort_key)
        else:
            recs.sort(key=lambda r: _expert_sort_key(r, user_rank))
        all_recs = grouped_all.get(name, recs)
        if sort_by_score or filters['profile_filter']:
            all_recs = sorted(all_recs, key=_score_desc_sort_key)
        else:
            all_recs = sorted(all_recs, key=lambda r: _expert_sort_key(r, user_rank))
        cards.append(_format_school_card(
            name, recs, user_rank, user_score, filters['cat_q'], all_recs,
        ))

    cards.sort(key=_school_card_sort_key)
    total = len(cards)
    limited = cards[:limit]
    return {
        'ok': True,
        'total': total,
        'records': limited,
        'view': 'school',
        'title': data.get('title'),
    }


def search_records(dataset_id, school='', major='', batch='', category='',
                   school_type='', provinces='', major_categories='',
                   major_groups='', user_rank=None, user_score=None,
                   limit=100, sort_by_score=False, view='', extra_schools=''):
    dataset_id = resolve_dataset_id(dataset_id)
    if is_strong_base_dataset(dataset_id):
        return search_strong_school_cards(
            dataset_id,
            school=school,
            major=major,
            user_score=user_score,
            limit=limit,
        )
    if view == 'school' and is_expert_dataset(dataset_id):
        return search_school_cards(
            dataset_id,
            school=school, major=major, batch=batch, category=category,
            school_type=school_type, provinces=provinces,
            major_categories=major_categories, major_groups=major_groups,
            user_rank=user_rank, user_score=user_score,
            limit=limit, sort_by_score=sort_by_score,
            extra_schools=extra_schools,
        )

    data = _load(dataset_id)
    if not data:
        return {'ok': False, 'message': '数据不存在', 'records': [], 'total': 0}

    filters = _prepare_search_filters(
        school, major, batch, category, school_type,
        provinces, major_categories, major_groups,
    )
    split_expert = is_expert_dataset(dataset_id)
    strong_base = is_strong_base_dataset(dataset_id)
    if strong_base:
        filters = dict(filters)
        filters['province_set'] = set()
        filters['profile_filter'] = bool(
            filters['category_titles'] or filters['major_name_set']
        )

    if not any([
        filters['school_q'], filters['major_q'], filters['batch_q'],
        filters['cat_q'], filters['type_q'], filters['profile_filter'],
    ]) and not split_expert and not strong_base:
        return {
            'ok': True, 'total': 0, 'records': [],
            'columns': data.get('columns'), 'title': data.get('title'),
        }

    matched_raw = []
    for rec in data.get('records') or []:
        if not _record_passes_filters(rec, filters, dataset_id):
            continue
        matched_raw.append(rec)

    total = len(matched_raw)
    if is_expert_dataset(dataset_id):
        if sort_by_score or filters['profile_filter']:
            matched_raw.sort(key=_score_desc_sort_key)
        else:
            matched_raw.sort(key=lambda r: _expert_sort_key(r, user_rank))

    matched = []
    for rec in matched_raw[:limit]:
        if is_expert_dataset(dataset_id):
            matched.append(format_expert_view(rec, user_rank, user_score))
        else:
            matched.append(rec)

    view_columns = None
    if is_expert_dataset(dataset_id):
        view_columns = [
            {'key': 'probability', 'label': '概率'},
            {'key': 'school_name', 'label': '大学'},
            {'key': 'major_name', 'label': '专业'},
            {'key': 'duration', 'label': '学制'},
            {'key': 'tuition', 'label': '学费'},
            {'key': 'plan_count', 'label': '专业招收人数'},
            {'key': 'school_type', 'label': '类型'},
            {'key': 'score_chart', 'label': '过去3年分数'},
            {'key': 'rank_chart', 'label': '过去3年专业位次'},
        ]

    return {
        'ok': True,
        'total': total,
        'records': matched,
        'columns': view_columns or data.get('columns'),
        'title': data.get('title'),
    }


def filter_options(dataset_id, batch=''):
    data = _load(dataset_id)
    if not data:
        return {'ok': False, 'batch': [], 'category': [], 'type': []}
    batch_q = (batch or '').strip()
    records = data.get('records') or []
    if batch_q:
        records = [
            rec for rec in records
            if _batch_matches(rec.get('batch'), batch_q)
        ]
    batches = sorted({str(r.get('batch') or '') for r in records if r.get('batch')})
    cats = sorted({str(r.get('category') or '') for r in records if r.get('category')})
    types = sorted({str(r.get('school_type') or '') for r in records if r.get('school_type')})
    return {'ok': True, 'batch': batches, 'category': cats, 'type': types}


def _group_code_matches(rec, group_code):
    gc = str(group_code or '').strip()
    if not gc or gc in ('强基', '—', '-'):
        return True
    rec_full = str(rec.get('major_group_code') or '').strip()
    rec_short = str(rec.get('group_code') or '').strip()
    if gc == rec_full or gc == rec_short:
        return True
    if rec_full and (rec_full == gc or rec_full.endswith(gc) or gc.endswith(rec_full)):
        return True
    return False


def _school_code_from_records(records, school_name):
    school_name = str(school_name or '').strip()
    if not school_name:
        return ''
    for rec in records or []:
        if str(rec.get('school_name') or '').strip() != school_name:
            continue
        code = str(rec.get('school_code') or '').strip()
        if code:
            return code
    return ''


def lookup_plan_prefer_meta(dataset_id, school_name='', group_code='', major_name='', batch_name=''):
    """从批次数据中补全院校代码、专业代码、学制、学费等。"""
    dataset_id = resolve_dataset_id(dataset_id)
    data = _load(dataset_id)
    school_name = str(school_name or '').strip()
    major_name = str(major_name or '').strip()
    group_code = str(group_code or '').strip()
    batch_q = (batch_name or '').strip()

    records = (data or {}).get('records') or []
    if batch_q:
        records = [rec for rec in records if _batch_matches(rec.get('batch'), batch_q)]
    school_code = _school_code_from_records(records, school_name)
    match = None

    if major_name:
        for rec in records:
            if str(rec.get('school_name') or '').strip() != school_name:
                continue
            if str(rec.get('major_name') or '').strip() != major_name:
                continue
            if not _group_code_matches(rec, group_code):
                continue
            match = rec
            break
        if not match:
            for rec in records:
                if str(rec.get('school_name') or '').strip() != school_name:
                    continue
                if str(rec.get('major_name') or '').strip() == major_name:
                    match = rec
                    break

    if not school_code and is_strong_base_dataset(dataset_id) and school_name:
        ds_meta = _DATASETS.get(resolve_dataset_id(dataset_id)) or {}
        prov = ds_meta.get('province') or '吉林'
        for alt_id in _expert_dataset_ids_for_province(prov):
            alt = _load(alt_id)
            school_code = _school_code_from_records((alt or {}).get('records'), school_name)
            if school_code:
                break

    if not match:
        return {
            'school_code': school_code,
            'major_code': '',
            'group_code': group_code,
            'duration': '',
            'tuition': '',
            'major_note': '',
            'rank_2025': '',
            'rank_max_2025': '',
        }

    canonical_group = str(
        match.get('major_group_code') or match.get('group_code') or group_code or ''
    ).strip()
    return {
        'school_code': school_code or str(match.get('school_code') or '').strip(),
        'major_code': str(match.get('major_code') or '').strip(),
        'group_code': canonical_group,
        'duration': str(match.get('duration') or '').strip(),
        'tuition': str(match.get('tuition') or '').strip(),
        'major_note': str(match.get('major_note') or '').strip(),
        'rank_2025': str(match.get('m2025_min_rank') or '').strip(),
        'rank_max_2025': str(match.get('m2025_max_rank') or '').strip(),
    }


def lookup_plan_prefer_batch(dataset_id, items, batch_name=''):
    results = []
    for item in items or []:
        if not isinstance(item, dict):
            results.append({})
            continue
        item_batch = (item.get('batch') or item.get('batch_name') or batch_name or '').strip()
        results.append(lookup_plan_prefer_meta(
            dataset_id,
            item.get('school_name') or item.get('schoolName') or '',
            item.get('group_code') or item.get('groupCode') or '',
            item.get('major_name') or item.get('majorName') or '',
            batch_name=item_batch,
        ))
    return results


def setup_sources(province='吉林'):
    """从桌面正式数据目录复制源 Excel（若存在）。"""
    province = norm_province(province) or '吉林'
    expert_map = discover_expert_files()
    strong_map = discover_strong_base_files()
    expert_src = expert_map.get(province)
    strong_src = strong_map.get(province)
    copied = copy_province_sources(province, expert_src, strong_src)
    if province == '吉林':
        if expert_src:
            _ensure_source(expert_src, os.path.basename(expert_src))
        if strong_src:
            _ensure_source(strong_src, os.path.basename(strong_src))
    return copied.get('expert') or expert_src, copied.get('strong') or strong_src


if __name__ == '__main__':
    import sys
    expert_src, strong_src = setup_sources('吉林')
    cmd = 'all'
    province = '吉林'
    for arg in sys.argv[1:]:
        if arg in ('expert', 'strong', 'all', 'setup', 'split', 'import-all', 'rebuild'):
            cmd = arg
        elif not arg.startswith('-'):
            province = norm_province(arg) or province
    if cmd == 'rebuild':
        rebuild_datasets_registry()
        print('datasets', len(_DATASETS))
    elif cmd == 'import-all':
        from import_gaokao_provinces import main as import_main
        raise SystemExit(import_main())
    else:
        if cmd in ('all', 'expert'):
            d = build_expert_json_for_province(province, xlsx_path=expert_src, copy_source=True)
            print(SYSTEM_TITLE, province, '本科批', d['counts'].get('undergraduate', 0))
        if cmd == 'split':
            results = split_expert_json_from_legacy()
            for bucket_key, payload in results.items():
                print(SYSTEM_TITLE, EXPERT_BATCH_BUCKETS[bucket_key]['title'], payload['count'])
        if cmd in ('all', 'strong'):
            d = build_strong_base_json_for_province(province, xlsx_path=strong_src, copy_source=True)
            print(SYSTEM_TITLE, province, '强基', d['count'])
        if province == '吉林' and cmd in ('all', 'expert', 'strong'):
            sync_jilin_legacy_json('吉林')
        rebuild_datasets_registry()


rebuild_datasets_registry()
