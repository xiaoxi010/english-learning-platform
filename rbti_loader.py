# rbti_loader.py
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
        print(f'[rbti] 读取失败 {path}: {e}')
        return None


@lru_cache(maxsize=1)
def load_questions():
    return _load('rbti_questions.json') or []


@lru_cache(maxsize=1)
def load_personalities():
    return _load('rbti_personalities.json') or {}


@lru_cache(maxsize=1)
def load_dimension_texts():
    return _load('rbti_dimensions.json') or {}


@lru_cache(maxsize=1)
def load_meta():
    return _load('rbti_meta.json') or {'name': 'RBTI', 'questionCount': 31}


def data_ready():
    return len(load_questions()) == 31 and bool(load_personalities())
