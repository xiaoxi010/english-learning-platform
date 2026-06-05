# feier_loader.py
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
        print(f'[feier] 读取失败 {path}: {e}')
        return None


@lru_cache(maxsize=1)
def load_questions():
    return _load('feier_questions.json') or []


@lru_cache(maxsize=1)
def load_score_table():
    return _load('feier_score_table.json') or []


@lru_cache(maxsize=1)
def load_result_bands():
    return _load('feier_results.json') or []


@lru_cache(maxsize=1)
def load_meta():
    return _load('feier_meta.json') or {'name': '菲尔人格测评', 'questionCount': 10}


def data_ready():
    qs = load_questions()
    st = load_score_table()
    return len(qs) == 10 and len(st) == 10 and bool(load_result_bands())
