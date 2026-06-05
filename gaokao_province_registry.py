# gaokao_province_registry.py — 各省专家版 / 强基数据目录与桌面源文件映射
"""每个省份在 data/gaokao_apply/provinces/{省名}/ 下独立存放 source 与 data.db。"""
import json
import os
import re
import shutil

from score_rank_loader import PROVINCE_LIST

_BASE = os.path.dirname(os.path.abspath(__file__))
GAOKAO_DATA_DIR = os.path.join(_BASE, 'data', 'gaokao_apply')
PROVINCES_DIR = os.path.join(GAOKAO_DATA_DIR, 'provinces')

DESKTOP_EXPERT_DIR = r'c:\Users\HP\Desktop\01-【正式数据】专家版2026'
DESKTOP_OTHER_DIR = r'c:\Users\HP\Desktop\03-【正式数据】其他数据2026'
DESKTOP_STRONG_DIR = os.path.join(DESKTOP_OTHER_DIR, '强基2025年计划分数线')

DEFAULT_DATA_YEAR = 2026
DEFAULT_RECORD_YEAR = 2025

PROVINCE_SLUG = {
    '北京': 'beijing',
    '天津': 'tianjin',
    '河北': 'hebei',
    '山西': 'shanxi',
    '内蒙古': 'neimenggu',
    '辽宁': 'liaoning',
    '吉林': 'jilin',
    '黑龙江': 'heilongjiang',
    '上海': 'shanghai',
    '江苏': 'jiangsu',
    '浙江': 'zhejiang',
    '安徽': 'anhui',
    '福建': 'fujian',
    '江西': 'jiangxi',
    '山东': 'shandong',
    '河南': 'henan',
    '湖北': 'hubei',
    '湖南': 'hunan',
    '广东': 'guangdong',
    '广西': 'guangxi',
    '海南': 'hainan',
    '重庆': 'chongqing',
    '四川': 'sichuan',
    '贵州': 'guizhou',
    '云南': 'yunnan',
    '西藏': 'xizang',
    '陕西': 'shaanxi',
    '甘肃': 'gansu',
    '青海': 'qinghai',
    '宁夏': 'ningxia',
    '新疆': 'xinjiang',
}

SLUG_TO_PROVINCE = {v: k for k, v in PROVINCE_SLUG.items()}

BATCH_KEYS = ('early', 'undergraduate', 'junior', 'strong')

BATCH_ALIAS = {
    'strong': 'strong',
    'strong_base': 'strong',
    '强基': 'strong',
    'early': 'early',
    'expert_early': 'early',
    '提前批': 'early',
    'undergraduate': 'undergraduate',
    'expert': 'undergraduate',
    'expert_undergraduate': 'undergraduate',
    '本科批': 'undergraduate',
    'junior': 'junior',
    'expert_junior': 'junior',
    '专科批': 'junior',
}


def norm_province(name):
    s = str(name or '').strip()
    if not s:
        return ''
    for suffix in ('维吾尔自治区', '回族自治区', '壮族自治区', '自治区', '省', '市'):
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[: -len(suffix)]
            break
    return s


def province_slug(province):
    p = norm_province(province)
    return PROVINCE_SLUG.get(p, re.sub(r'[^a-z0-9]+', '_', p.lower()) if p else '')


def province_dir(province):
    p = norm_province(province)
    if not p:
        raise ValueError('province required')
    return os.path.join(PROVINCES_DIR, p)


def province_source_dir(province):
    return os.path.join(province_dir(province), 'source')


PROVINCE_DB_NAME = 'data.undergraduate.db'


def province_db_path(province):
    from gaokao_db import province_db_undergraduate
    return province_db_undergraduate(province)


def province_json_name(batch_key):
    if batch_key == 'strong':
        return 'strong_base.json'
    return f'expert_{batch_key}.json'


def province_json_path(province, batch_key):
    return os.path.join(province_dir(province), province_json_name(batch_key))


def province_manifest_path(province):
    return os.path.join(province_dir(province), 'manifest.json')


def dataset_id(province, batch_key, year=None):
    slug = province_slug(province)
    y = year or DEFAULT_DATA_YEAR
    if batch_key == 'strong':
        return f'{slug}_{y}_strong_base'
    return f'{slug}_{y}_expert_{batch_key}'


def legacy_jilin_dataset_id(batch_key):
    if batch_key == 'strong':
        return 'jilin_2025_strong_base'
    return f'jilin_2025_expert_{batch_key}'


def ensure_province_layout(province):
    root = province_dir(province)
    src = province_source_dir(province)
    os.makedirs(src, exist_ok=True)
    return {'root': root, 'source': src}


def write_manifest(province, meta=None):
    meta = meta or {}
    p = norm_province(province)
    payload = {
        'province': p,
        'slug': province_slug(p),
        'data_year': meta.get('data_year', DEFAULT_DATA_YEAR),
        'record_year': meta.get('record_year', DEFAULT_RECORD_YEAR),
        'expert_source': meta.get('expert_source', ''),
        'strong_source': meta.get('strong_source', ''),
        'datasets': {
            batch_key: dataset_id(p, batch_key, meta.get('data_year', DEFAULT_DATA_YEAR))
            for batch_key in BATCH_KEYS
        },
        'counts': meta.get('counts', {}),
        'imported_at': meta.get('imported_at', ''),
    }
    for key in (
        'batch_labels', 'storage', 'db_file', 'db_part2', 'db_part3',
        'db_undergraduate', 'db_other', 'db_undergraduate_part2', 'db_undergraduate_part3',
        'db_other_part2', 'db_other_part3', 'expert_import',
    ):
        if key in meta:
            payload[key] = meta[key]
    path = province_manifest_path(p)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def read_manifest(province):
    path = province_manifest_path(province)
    if not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_imported_provinces():
    if not os.path.isdir(PROVINCES_DIR):
        return []
    out = []
    for name in sorted(os.listdir(PROVINCES_DIR)):
        root = os.path.join(PROVINCES_DIR, name)
        if not os.path.isdir(root):
            continue
        manifest = read_manifest(name)
        try:
            from gaokao_db import batch_exists, province_has_db
            has_db = province_has_db(name)
            has_expert = has_db and (
                batch_exists(name, 'undergraduate')
                or batch_exists(name, 'early')
                or batch_exists(name, 'junior')
            )
            has_strong = has_db and batch_exists(name, 'strong')
        except Exception:
            db_path = province_db_path(name)
            has_db = os.path.isfile(db_path)
            has_expert = has_db
            has_strong = has_db
        else:
            undergrad = province_json_path(name, 'undergraduate')
            has_expert = os.path.isfile(undergrad)
            has_strong = os.path.isfile(province_json_path(name, 'strong'))
        out.append({
            'province': name,
            'slug': province_slug(name),
            'manifest': manifest,
            'has_expert': has_expert,
            'has_strong': has_strong,
            'has_db': has_db,
        })
    return out


def _score_expert_filename(filename, full_path):
    score = 0
    if '完整' in filename or '录取数据' in filename:
        score += 100
    if '数据' in filename:
        score += 20
    if filename.lower().endswith('.xlsx'):
        score += 5
    try:
        score += min(os.path.getsize(full_path) // (1024 * 1024), 50)
    except OSError:
        pass
    return score


def guess_province_from_filename(filename):
    base = os.path.basename(filename)
    base = re.sub(r'^\d+[、.]?\s*', '', base)
    ordered = sorted(PROVINCE_SLUG.keys(), key=len, reverse=True)
    for prov in ordered:
        if prov in base:
            return prov
    m = re.match(r'^(.+?)（20\d{2}', base)
    if m:
        return norm_province(m.group(1))
    return ''


def discover_expert_files(desktop_dir=None):
    desktop_dir = desktop_dir or DESKTOP_EXPERT_DIR
    if not os.path.isdir(desktop_dir):
        return {}
    grouped = {}
    for filename in os.listdir(desktop_dir):
        lower = filename.lower()
        if not (lower.endswith('.xlsx') or lower.endswith('.xls')):
            continue
        full = os.path.join(desktop_dir, filename)
        prov = guess_province_from_filename(filename)
        if not prov:
            continue
        prev = grouped.get(prov)
        if not prev or _score_expert_filename(filename, full) > _score_expert_filename(
            os.path.basename(prev), prev
        ):
            grouped[prov] = full
    return grouped


def discover_strong_base_files(desktop_dir=None):
    desktop_dir = desktop_dir or DESKTOP_STRONG_DIR
    if not os.path.isdir(desktop_dir):
        return {}
    out = {}
    for filename in os.listdir(desktop_dir):
        lower = filename.lower()
        if not (lower.endswith('.xlsx') or lower.endswith('.xls')):
            continue
        if '强基' not in filename and '分数线' not in filename:
            continue
        full = os.path.join(desktop_dir, filename)
        prov = ''
        m = re.search(r'分数线\s*[-－—]\s*(.+?)\.', filename)
        if m:
            prov = norm_province(m.group(1))
        if not prov:
            prov = guess_province_from_filename(filename)
        if prov and prov not in out:
            out[prov] = full
    return out


def copy_province_sources(province, expert_path=None, strong_path=None):
    layout = ensure_province_layout(province)
    copied = {}
    if expert_path and os.path.isfile(expert_path):
        ext = os.path.splitext(expert_path)[1].lower() or '.xlsx'
        dest = os.path.join(layout['source'], f'expert{ext}')
        shutil.copy2(expert_path, dest)
        copied['expert'] = dest
    if strong_path and os.path.isfile(strong_path):
        ext = os.path.splitext(strong_path)[1].lower() or '.xlsx'
        dest = os.path.join(layout['source'], f'strong_base{ext}')
        shutil.copy2(strong_path, dest)
        copied['strong'] = dest
    return copied


def province_apply_available(province):
    p = norm_province(province)
    if not p:
        return False
    try:
        from gaokao_db import batch_exists, dataset_count, province_has_db
    except Exception:
        province_has_db = lambda _x: os.path.isfile(province_db_path(p))
        batch_exists = dataset_count = None
    if province_has_db(p):
        try:
            for bk in ('undergraduate', 'early', 'junior', 'strong'):
                if batch_exists(p, bk) and dataset_count(p, bk) > 0:
                    return True
        except Exception:
            return True
    undergrad = province_json_path(p, 'undergraduate')
    strong = province_json_path(p, 'strong')
    if os.path.isfile(undergrad):
        return True
    if os.path.isfile(strong):
        return True
    legacy = os.path.join(GAOKAO_DATA_DIR, legacy_jilin_dataset_id('undergraduate') + '.json')
    if p == '吉林' and os.path.isfile(legacy):
        return True
    return False


def list_apply_provinces_status():
    rows = []
    for prov in PROVINCE_LIST:
        manifest = read_manifest(prov)
        counts = (manifest or {}).get('counts') or {}
        expert_count = sum(
            int(counts.get(k) or 0)
            for k in ('early', 'undergraduate', 'junior')
        )
        strong_count = int(counts.get('strong') or 0)
        rows.append({
            'province': prov,
            'slug': province_slug(prov),
            'available': province_apply_available(prov),
            'expert_count': expert_count,
            'strong_count': strong_count,
            'total_count': expert_count + strong_count,
            'manifest': manifest,
        })
    return rows
