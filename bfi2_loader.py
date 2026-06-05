# bfi2_loader.py
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
        print(f'[bfi2] 读取失败 {path}: {e}')
        return None


@lru_cache(maxsize=1)
def load_questions():
    return _load('bfi2_questions.json') or []


@lru_cache(maxsize=1)
def load_rating_scale():
    return _load('bfi2_rating_scale.json') or {}


@lru_cache(maxsize=1)
def load_dimensions():
    return _load('bfi2_dimensions.json') or {}


@lru_cache(maxsize=1)
def load_norms():
    return _load('bfi2_norms.json') or {}


@lru_cache(maxsize=1)
def load_match_meta():
    return _load('bfi2_match_meta.json') or {}


@lru_cache(maxsize=1)
def load_meta():
    return _load('bfi2_meta.json') or {
        'name': 'BFI-2 大五人格量表',
        'questionCount': 60,
    }


def data_ready():
    return len(load_questions()) == 60 and bool(load_dimensions()) and bool(load_norms())
