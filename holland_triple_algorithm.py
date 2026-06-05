# holland_triple_algorithm.py — 霍兰德三维码优先级（对齐 霍兰德三维结果算法.js）
import json
import os

RIASEC = ['R', 'I', 'A', 'S', 'E', 'C']

_BASE = os.path.dirname(os.path.abspath(__file__))
_PRIORITY_PATHS = [
    os.path.join(_BASE, 'data', 'holland_code_priority.json'),
    os.path.join(
        r'C:\Users\HP\Desktop\吉致生涯\吉致生涯\life_code\miniprogram\utils',
        '霍兰德三维结果算法.js',
    ),
]


def _load_priority():
    for path in _PRIORITY_PATHS:
        if not os.path.isfile(path):
            continue
        if path.endswith('.json'):
            with open(path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
    return {}


HOLLAND_CODE_PRIORITY = _load_priority()


def normalize_scores(scores):
    s = {}
    for k in RIASEC:
        v = (scores or {}).get(k)
        s[k] = int(v) if v is not None and str(v).strip() != '' else 0
    return s


def top_three_letters_by_score(scores):
    s = normalize_scores(scores)
    arr = [{'k': k, 'v': s[k]} for k in RIASEC]
    arr.sort(key=lambda x: (-x['v'], RIASEC.index(x['k'])))
    return [arr[0]['k'], arr[1]['k'], arr[2]['k']]


def get_unique_holland_code(scores):
    L1, L2, L3 = top_three_letters_by_score(scores)
    straight = L1 + L2 + L3
    swap23 = L1 + L3 + L2
    p_straight = HOLLAND_CODE_PRIORITY.get(straight, 999)
    p_swap = HOLLAND_CODE_PRIORITY.get(swap23, 999)
    if p_swap < p_straight:
        return swap23
    if p_straight < p_swap:
        return straight
    return straight if straight <= swap23 else swap23
