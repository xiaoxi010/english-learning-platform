# feier_calc.py — 与小程序 菲尔人格测评数据库.js 一致
from __future__ import annotations

from feier_loader import load_result_bands, load_score_table


def compute_feier_total_score(answers: list[str]) -> int:
    table = load_score_table()
    if len(answers) != len(table):
        return 0
    total = 0
    for i, letter in enumerate(answers):
        row = table[i]
        pts = row.get((letter or '').strip().upper())
        if isinstance(pts, (int, float)):
            total += int(pts)
    return total


def get_feier_result_meta(total: int) -> dict:
    score = int(total) if isinstance(total, (int, float)) and total == total else 0
    bands = load_result_bands()
    band = bands[0] if bands else {}
    for b in bands:
        if score >= b.get('min', 0) and score <= b.get('max', 999):
            band = b
            break
    return {**band, 'score': score, 'totalScore': score}
