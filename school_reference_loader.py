# school_reference_loader.py — 院校筛选 / 学校介绍 / 学科评估 参考库
import json
import os
import re
import shutil

_BASE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_BASE, 'data', 'gaokao_apply')
_SOURCE_DIR = os.path.join(_DATA_DIR, 'source')

PROFILE_TXT = os.path.join(_SOURCE_DIR, '院校筛选系统数据库.txt')
INTRO_TXT = os.path.join(_SOURCE_DIR, '学校介绍.txt')
EVAL_TXT = os.path.join(_SOURCE_DIR, '学科评估.txt')

SCHOOL_REFERENCE_JSON = os.path.join(_DATA_DIR, 'school_reference.json')

_DESKTOP_PROFILE = r'c:\Users\HP\Desktop\院校筛选系统数据库.txt'
_DESKTOP_INTRO = r'c:\Users\HP\Desktop\学校介绍.txt'
_DESKTOP_EVAL = r'c:\Users\HP\Desktop\学科评估.txt'

_CACHE = None

_QUOTED_FIELD_RE = re.compile(r'(\w+):\s*"((?:\\.|[^"\\])*)"')
_BRACKET_FIELD_RE = re.compile(r'(\w+):\s*\[(.*?)\]', re.DOTALL)
_INTRO_ENTRY_RE = re.compile(r'"((?:\\.|[^"\\])*)"\s*:\s*\{', re.DOTALL)
_EVAL_PAIR_RE = re.compile(r'"((?:\\.|[^"\\])*)"\s*:\s*"((?:\\.|[^"\\])*)"')


def _ensure_sources():
    os.makedirs(_SOURCE_DIR, exist_ok=True)
    pairs = [
        (_DESKTOP_PROFILE, '院校筛选系统数据库.txt'),
        (_DESKTOP_INTRO, '学校介绍.txt'),
        (_DESKTOP_EVAL, '学科评估.txt'),
    ]
    for src, name in pairs:
        dest = os.path.join(_SOURCE_DIR, name)
        if os.path.isfile(src) and (
            not os.path.isfile(dest) or os.path.getmtime(src) > os.path.getmtime(dest)
        ):
            shutil.copy2(src, dest)


def _split_bracket_items(raw):
    if not raw or not str(raw).strip():
        return []
    out = []
    for part in re.split(r'\s*,\s*', str(raw).strip()):
        part = part.strip().strip('"').strip("'")
        if part:
            out.append(part)
    return out


def _parse_profile_line(line):
    line = (line or '').strip().rstrip(',')
    if not line.startswith('{') or not line.endswith('}'):
        return None
    body = line[1:-1]
    name_m = re.search(r'name:\s*"([^"]*)"', body)
    if not name_m:
        return None
    rec = {'name': name_m.group(1).strip()}
    for key in ('province', 'city', 'subject', 'nature', 'ranking'):
        m = re.search(rf'{key}:\s*"([^"]*)"', body)
        if m:
            rec[key] = m.group(1).strip()
    label_m = re.search(r'label:\s*\[(.*?)\]', body, re.DOTALL)
    if label_m:
        rec['label'] = _split_bracket_items(label_m.group(1))
    type_m = re.search(r'type:\s*\[(.*?)\]', body, re.DOTALL)
    if type_m:
        rec['type'] = _split_bracket_items(type_m.group(1))
    rec.setdefault('label', [])
    rec.setdefault('type', [])
    return rec


def _parse_profile_file(path):
    records = []
    if not os.path.isfile(path):
        return records
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = _parse_profile_line(line)
            if rec and rec.get('name'):
                records.append(rec)
    return records


def _extract_braced_object(text, start_idx):
    depth = 0
    i = start_idx
    while i < len(text):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start_idx:i + 1], i + 1
        i += 1
    return '', len(text)


def _parse_kv_object(raw):
    out = {}
    if not raw:
        return out
    for m in _QUOTED_FIELD_RE.finditer(raw):
        key = m.group(1)
        val = m.group(2).replace('\\"', '"').strip()
        if val not in ('', '/'):
            out[key] = val
    return out


def _parse_map_file(path):
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    pos = 0
    while pos < len(text):
        m = _INTRO_ENTRY_RE.search(text, pos)
        if not m:
            break
        name = m.group(1).replace('\\"', '"').strip()
        obj_start = m.end() - 1
        obj_raw, next_pos = _extract_braced_object(text, obj_start)
        pos = next_pos
        if not name:
            continue
        if path.endswith('学科评估.txt'):
            evals = {}
            for em in _EVAL_PAIR_RE.finditer(obj_raw):
                disc = em.group(1).strip()
                grade = em.group(2).strip()
                if disc and grade:
                    evals[disc] = grade
            out[name] = evals
        else:
            out[name] = _parse_kv_object(obj_raw[1:-1])
    return out


def build_school_reference_json(
    profile_path=None,
    intro_path=None,
    eval_path=None,
    json_path=None,
):
    _ensure_sources()
    profile_path = profile_path or PROFILE_TXT
    intro_path = intro_path or INTRO_TXT
    eval_path = eval_path or EVAL_TXT
    json_path = json_path or SCHOOL_REFERENCE_JSON

    profiles = _parse_profile_file(profile_path)
    intros = _parse_map_file(intro_path)
    evals = _parse_map_file(eval_path)

    by_name = {}
    for prof in profiles:
        name = prof['name']
        by_name[name] = {
            'name': name,
            'province': prof.get('province') or '',
            'city': prof.get('city') or '',
            'subject': prof.get('subject') or '',
            'nature': prof.get('nature') or '',
            'ranking': prof.get('ranking') or '',
            'label': prof.get('label') or [],
            'type': prof.get('type') or [],
            'intro': intros.get(name) or {},
            'discipline_eval': evals.get(name) or {},
        }

    for name, intro in intros.items():
        if name in by_name:
            by_name[name]['intro'] = intro
        else:
            by_name[name] = {
                'name': name,
                'province': '',
                'city': '',
                'subject': '',
                'nature': '',
                'ranking': '',
                'label': [],
                'type': [],
                'intro': intro,
                'discipline_eval': evals.get(name) or {},
            }

    for name, disc in evals.items():
        if name in by_name:
            by_name[name]['discipline_eval'] = disc

    payload = {
        'count': len(by_name),
        'schools': by_name,
    }
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    global _CACHE
    _CACHE = payload
    return payload


def load_school_reference():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if os.path.isfile(SCHOOL_REFERENCE_JSON):
        with open(SCHOOL_REFERENCE_JSON, 'r', encoding='utf-8') as f:
            _CACHE = json.load(f)
        return _CACHE
    try:
        return build_school_reference_json()
    except OSError:
        _CACHE = {'count': 0, 'schools': {}}
        return _CACHE


def lookup_school_profile(school_name):
    data = load_school_reference()
    schools = data.get('schools') or {}
    name = (school_name or '').strip()
    if not name:
        return None
    if name in schools:
        return schools[name]
    compact = name.replace(' ', '')
    for key, val in schools.items():
        if key.replace(' ', '') == compact:
            return val
    for key, val in schools.items():
        if compact in key.replace(' ', '') or key.replace(' ', '') in compact:
            return val
    return None


def top_discipline_tags(profile, limit=4):
    disc = (profile or {}).get('discipline_eval') or {}
    if not disc:
        return []
    order = {'A+': 0, 'A': 1, 'A-': 2, 'B+': 3, 'B': 4, 'B-': 5}
    items = sorted(disc.items(), key=lambda x: (order.get(x[1], 9), x[0]))
    return [f'{k}{v}' for k, v in items[:limit]]


if __name__ == '__main__':
    payload = build_school_reference_json()
    print('schools', payload['count'], '->', SCHOOL_REFERENCE_JSON)
    sample = lookup_school_profile('重庆大学')
    print('sample', sample.get('name') if sample else None, sample.get('label')[:3] if sample else None)
