# mbti_loader.py
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
        print(f'[mbti] 读取失败 {path}: {e}')
        return None


@lru_cache(maxsize=1)
def load_questions():
    return _load('mbti_questions.json') or []


@lru_cache(maxsize=1)
def load_likert():
    return _load('mbti_likert.json') or []


@lru_cache(maxsize=1)
def load_types():
    return _load('mbti_types.json') or {}


@lru_cache(maxsize=1)
def load_meta():
    return _load('mbti_meta.json') or {'name': 'MBTI 趣味测评', 'questionCount': 48}


def data_ready():
    return len(load_questions()) == 48 and bool(load_types())
