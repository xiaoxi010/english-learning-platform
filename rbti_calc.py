# rbti_calc.py — 与小程序 RBTIscore.js 一致
from __future__ import annotations

R_SUB = ['C1', 'C7', 'C11']
B_SUB = ['C2', 'C6', 'C9']
T_SUB = ['C3', 'C8', 'C10']
I_SUB = ['C4', 'C5', 'C12']

MAPPING = [
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C4', 'B': 'C3', 'C': 'C1', 'D': 'C6'},
    {'A': 'C6', 'B': 'C1', 'C': 'C3', 'D': 'C4'},
    {'A': 'C4', 'B': 'C1', 'C': 'C6', 'D': 'C3'},
    {'A': 'C4', 'B': 'C3', 'C': 'C6', 'D': 'C1'},
    {'A': 'C4', 'B': 'C1', 'C': 'C6', 'D': 'C3'},
    {'A': 'C3', 'B': 'C4', 'C': 'C6', 'D': 'C1'},
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C4', 'B': 'C1', 'C': 'C6', 'D': 'C9'},
    {'A': 'C4', 'B': 'C1', 'C': 'C6', 'D': 'C3'},
    {'A': 'C1', 'B': 'C6', 'C': 'C3', 'D': 'C4'},
    {'A': 'C4', 'B': 'C6', 'C': 'C3', 'D': 'C1'},
    {'A': 'C4', 'B': 'C6', 'C': 'C3', 'D': 'C1'},
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C3', 'B': 'C6', 'C': 'C1', 'D': 'C4'},
    {'A': 'C1', 'B': 'C6', 'C': 'C3', 'D': 'C4'},
    {'A': 'C6', 'B': 'C3', 'C': 'C1', 'D': 'C4'},
    {'A': 'C4', 'B': 'C3', 'C': 'C6', 'D': 'C1'},
    {'A': 'C4', 'B': 'C6', 'C': 'C3', 'D': 'C1'},
    {'A': 'C3', 'B': 'C6', 'C': 'C4', 'D': 'C1'},
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C4', 'B': 'C3', 'C': 'C1', 'D': 'C6'},
    {'A': 'C4', 'B': 'C9', 'C': 'C1', 'D': 'C3'},
    {'A': 'C4', 'B': 'C3', 'C': 'C6', 'D': 'C1'},
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C4', 'B': 'C3', 'C': 'C6', 'D': 'C1'},
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C4', 'B': 'C6', 'C': 'C1', 'D': 'C3'},
    {'A': 'C3', 'B': 'C6', 'C': 'C1', 'D': 'C4'},
]

MAX_DIM = 31
VALID_ANS = frozenset({'A', 'B', 'C', 'D'})


def _spread_sub_facet(cluster: str, question_index: int) -> str:
    qi = question_index % 3
    if cluster in R_SUB:
        return R_SUB[qi]
    if cluster in B_SUB:
        return B_SUB[qi]
    if cluster in T_SUB:
        return T_SUB[qi]
    if cluster in I_SUB:
        return I_SUB[qi]
    return cluster


def calculate_rbti(answers: list[str]) -> dict:
    if len(answers) != 31:
        raise ValueError('题目和答案数量必须为 31 道')

    scores = {f'C{i}': 0 for i in range(1, 13)}

    for index, answer in enumerate(answers):
        row = MAPPING[index]
        raw = row.get(answer)
        if raw:
            dim = _spread_sub_facet(raw, index)
            scores[dim] += 1

    r = scores['C1'] + scores['C7'] + scores['C11']
    b = scores['C2'] + scores['C6'] + scores['C9']
    t = scores['C3'] + scores['C8'] + scores['C10']
    i = scores['C4'] + scores['C5'] + scores['C12']
    total = r + b + t + i
    avg = total / 4 if total else 0

    type_code = (
        f"{'H' if r >= avg else 'L'}"
        f"{'H' if b >= avg else 'L'}"
        f"{'H' if t >= avg else 'L'}"
        f"{'H' if i >= avg else 'L'}"
    )

    return {
        'scores': scores,
        'dimensions': {'R': r, 'B': b, 'T': t, 'I': i},
        'typeCode': type_code,
        'total': total,
    }
