# cattell_loader.py
import json
import os
from functools import lru_cache

_BASE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_BASE, 'data')


def _load(name):
    path = os.path.join(_DATA, name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f'[cattell] 读取失败 {path}: {e}')
        return None


@lru_cache(maxsize=1)
def load_questions():
    return _load('cattell_questions.json') or []


@lru_cache(maxsize=1)
def load_scoring():
    return _load('cattell_scoring.json') or {}


@lru_cache(maxsize=1)
def load_norms():
    return _load('cattell_norms.json') or {}


@lru_cache(maxsize=1)
def load_dimensions():
    return _load('cattell_dimensions.json') or []


@lru_cache(maxsize=1)
def load_secondary():
    return _load('cattell_secondary.json') or []


@lru_cache(maxsize=1)
def load_careers():
    return _load('cattell_careers.json') or []


@lru_cache(maxsize=1)
def load_meta():
    return _load('cattell_meta.json') or {
        'name': '卡特尔 16PF 人格因素测评',
        'questionCount': 187,
    }


def data_ready():
    return len(load_questions()) == 187 and bool(load_scoring()) and bool(load_norms())
