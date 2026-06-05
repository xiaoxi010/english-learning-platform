# constellation_loader.py — 星血测评文案库
import json
import os
from functools import lru_cache

_BASE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(_BASE, 'data', 'constellation.json'),
    os.path.join(_BASE, 'data', 'constellation_source.json'),
    os.path.join(
        r'e:\xwechat_files\wxid_6kz7tqac90kx22_67a2\msg\file\2026-05',
        'constellation.json',
    ),
]


def _normalize_payload(obj):
    if not obj or not isinstance(obj, dict):
        return None
    if isinstance(obj.get('constellation_attribute'), dict):
        return obj
    for key in ('data', 'content', 'constellationData', 'payload', 'body'):
        inner = obj.get(key)
        if isinstance(inner, dict) and isinstance(inner.get('constellation_attribute'), dict):
            return inner
    if isinstance(obj.get('json'), str):
        try:
            return _normalize_payload(json.loads(obj['json']))
        except json.JSONDecodeError:
            return None
    return None


@lru_cache(maxsize=1)
def load_constellation_data():
    for path in _CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                raw = json.load(f)
            data = _normalize_payload(raw) or raw
            if isinstance(data.get('constellation_attribute'), dict):
                return data
        except (OSError, json.JSONDecodeError) as e:
            print(f'[constellation] 读取失败 {path}: {e}')
    return {}


def data_ready():
    return bool(load_constellation_data().get('constellation_attribute'))
