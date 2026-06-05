# lifeway_loader.py - 加载人生道路解读数据库 lifeway.json
import json
import os
from functools import lru_cache

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_PATHS = [
    os.path.join(_BASE_DIR, 'data', 'lifeway.json'),
    os.path.join(_BASE_DIR, 'data', 'lifeway.js'),
    os.path.join(
        r'e:\xwechat_files\wxid_6kz7tqac90kx22_67a2\msg\file\2026-05',
        'lifeway.js',
    ),
    os.path.join(
        r'C:\Users\HP\Desktop\吉致生涯\吉致生涯\life_code\miniprogram\pages',
        'lifeway.json',
    ),
]


def _normalize_payload(obj):
    if not obj or not isinstance(obj, dict):
        return None
    if isinstance(obj.get('person_year_word'), dict):
        return obj
    for key in ('data', 'content', 'payload', 'body', 'lifewayData'):
        inner = obj.get(key)
        if isinstance(inner, dict) and isinstance(inner.get('person_year_word'), dict):
            return inner
    if isinstance(obj.get('json'), str):
        try:
            return _normalize_payload(json.loads(obj['json']))
        except json.JSONDecodeError:
            return None
    return None


def _load_lifeway_js(path):
    import subprocess

    script = os.path.join(_BASE_DIR, 'scripts', 'export_lifeway_data.js')
    if not os.path.isfile(script):
        return None
    try:
        proc = subprocess.run(
            ['node', script, path],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=_BASE_DIR,
            check=False,
        )
        if proc.returncode != 0:
            print(f'[lifeway] JS 解析失败 {path}: {proc.stderr or proc.stdout}')
            return None
        json_path = os.path.join(_BASE_DIR, 'data', 'lifeway.json')
        if os.path.isfile(json_path):
            with open(json_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f'[lifeway] JS 转 JSON 失败 {path}: {e}')
    return None


@lru_cache(maxsize=1)
def load_lifeway_data():
    for path in _CANDIDATE_PATHS:
        if not os.path.isfile(path):
            continue
        try:
            if path.lower().endswith('.js'):
                raw = _load_lifeway_js(path)
                if raw and isinstance(raw.get('person_year_word'), dict):
                    return raw
                continue
            with open(path, 'r', encoding='utf-8-sig') as f:
                raw = json.load(f)
            data = _normalize_payload(raw) or raw
            if isinstance(data.get('person_year_word'), dict):
                return data
        except (OSError, json.JSONDecodeError) as e:
            print(f'[lifeway] 读取失败 {path}: {e}')
    print(
        '[lifeway] 未找到 lifeway.json，请放到：\n'
        f'  {_CANDIDATE_PATHS[0]}'
    )
    return {}


def lifeway_ready():
    return bool(load_lifeway_data().get('person_year_word'))
