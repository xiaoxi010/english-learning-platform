# personality_loader.py - 加载生命密码解读数据库 Personality.json
import json
import os
from functools import lru_cache

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_PATHS = [
    os.path.join(_BASE_DIR, 'data', 'Personality.json'),
    os.path.join(_BASE_DIR, 'data', 'Personality.js'),
    os.path.join(
        r'e:\xwechat_files\wxid_6kz7tqac90kx22_67a2\msg\file\2026-05',
        'Personality.js',
    ),
    os.path.join(
        r'C:\Users\HP\Desktop\吉致生涯\吉致生涯\life_code\miniprogram\pages',
        'Personality.json',
    ),
]


def _normalize_payload(obj):
    if not obj or not isinstance(obj, dict):
        return None
    if isinstance(obj.get('Positively'), dict):
        return obj
    for key in ('data', 'content', 'payload', 'body', 'personalityData'):
        inner = obj.get(key)
        if isinstance(inner, dict) and isinstance(inner.get('Positively'), dict):
            return inner
    if isinstance(obj.get('json'), str):
        try:
            parsed = json.loads(obj['json'])
            return _normalize_payload(parsed)
        except json.JSONDecodeError:
            return None
    return None


@lru_cache(maxsize=1)
def _load_personality_js(path):
    """解析 const personalityData = {...}; export default ... 的 JS 文件"""
    import subprocess
    script = os.path.join(_BASE_DIR, 'scripts', 'export_personality_data.js')
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
            print(f'[personality] JS 解析失败 {path}: {proc.stderr or proc.stdout}')
            return None
        json_path = os.path.join(_BASE_DIR, 'data', 'Personality.json')
        if os.path.isfile(json_path):
            with open(json_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f'[personality] JS 转 JSON 失败 {path}: {e}')
    return None


def load_personality_data():
    """加载 Personality.json / Personality.js，失败返回空 dict"""
    for path in _CANDIDATE_PATHS:
        if not os.path.isfile(path):
            continue
        try:
            if path.lower().endswith('.js'):
                raw = _load_personality_js(path)
                if raw and isinstance(raw.get('Positively'), dict):
                    return raw
                continue
            with open(path, 'r', encoding='utf-8-sig') as f:
                raw = json.load(f)
            data = _normalize_payload(raw) or raw
            if isinstance(data, dict) and isinstance(data.get('Positively'), dict):
                return data
        except (OSError, json.JSONDecodeError) as e:
            print(f'[personality] 读取失败 {path}: {e}')
    print(
        '[personality] 未找到 Personality.json，请将小程序云数据库/云存储中的文件放到：\n'
        f'  {_CANDIDATE_PATHS[0]}'
    )
    return {}


def personality_ready():
    data = load_personality_data()
    return bool(data.get('Positively'))
