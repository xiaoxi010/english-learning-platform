# eysenck_loader.py
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
        print(f'[eysenck] 读取失败 {path}: {e}')
        return None


@lru_cache(maxsize=1)
def load_questions():
    return _load('eysenck_questions.json') or []


@lru_cache(maxsize=1)
def load_scoring():
    return _load('eysenck_scoring.json') or {'dimensions': {}}


@lru_cache(maxsize=1)
def load_dimensions():
    return _load('eysenck_dimensions.json') or []


@lru_cache(maxsize=1)
def load_patterns():
    return _load('eysenck_patterns.json') or {'typicalPatterns': [], 'triggerPoints': {}}


@lru_cache(maxsize=1)
def load_meta():
    return _load('eysenck_meta.json') or {
        'name': '艾克森情绪稳定性测评',
        'questionCount': 210,
    }


def data_ready():
    return len(load_questions()) == 210 and bool(load_scoring().get('dimensions'))
