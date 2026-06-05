# holland_loader.py — 霍兰德题库与解读数据
import json
import os
from functools import lru_cache

_BASE = os.path.dirname(os.path.abspath(__file__))
_MINI = r'C:\Users\HP\Desktop\吉致生涯\吉致生涯\life_code\miniprogram'

QUESTION_PATHS = [
    os.path.join(_BASE, 'data', 'holland_questions.json'),
    os.path.join(_MINI, 'utils', '霍兰德职业兴趣测试题.js'),
]
DIMENSION_PATHS = [
    os.path.join(_BASE, 'data', 'holland_dimensions.json'),
]
TRIPLE_PATHS = [
    os.path.join(_BASE, 'data', 'holland_triple_careers.json'),
]


def _load_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f'[holland] 读取失败 {path}: {e}')
        return None


def _load_questions_from_node():
    try:
        import subprocess
        script = (
            "const q=require(process.argv[1]);"
            "process.stdout.write(JSON.stringify(q.HOLLAND_QUESTIONS));"
        )
        js_path = os.path.join(_MINI, 'utils', '霍兰德职业兴趣测试题.js')
        if not os.path.isfile(js_path):
            return None
        r = subprocess.run(
            ['node', '-e', script, js_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30,
            cwd=_BASE,
        )
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception as e:
        print(f'[holland] node 导出题目失败: {e}')
    return None


@lru_cache(maxsize=1)
def load_questions():
    for path in QUESTION_PATHS:
        if path.endswith('.json'):
            data = _load_json(path)
            if data:
                return data
    return _load_questions_from_node() or []


@lru_cache(maxsize=1)
def load_dimensions():
    for path in DIMENSION_PATHS:
        data = _load_json(path)
        if data:
            return data
    return {}


@lru_cache(maxsize=1)
def load_triple_careers():
    for path in TRIPLE_PATHS:
        data = _load_json(path)
        if data:
            return data
    return {}


def data_ready():
    return len(load_questions()) > 0 and len(load_dimensions()) >= 6
