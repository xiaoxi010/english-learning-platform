# subject_code.py - 学科码与坐镇码（对齐 subjectCodeFromBirth.js / subject.js）
import re


def _digits_only(s: str) -> str:
    return re.sub(r'\D', '', str(s or ''))


def sum_s(num1, num2) -> int:
    n1, n2 = int(num1 or 0), int(num2 or 0)
    s = n1 + n2
    if s > 9:
        return s // 10 + s % 10
    return s


def sum_ss(num1, num2) -> int:
    n1, n2 = int(num1 or 0), int(num2 or 0)
    s = n1 + n2
    if s == 0:
        return 5
    if s % 9 == 0:
        return 9
    return s % 9


def get_subject_code_from_birth(birth_number: str) -> str:
    """主金字塔底层四位数字拼接"""
    s = _digits_only(birth_number)
    if len(s) != 8:
        return ''
    digits = list(s)
    year = digits[:4]
    day = digits[4:8]
    tlr = list(reversed(day)) + year
    i1 = [sum_s(tlr[0], tlr[1]), sum_s(tlr[2], tlr[3]),
          sum_s(tlr[4], tlr[5]), sum_ss(tlr[6], tlr[7])]
    return f'{i1[0]}{i1[1]}{i1[2]}{i1[3]}'


def compute_supervisor_code(birth_number: str):
    s = _digits_only(birth_number)
    if len(s) != 8:
        return None
    digits = list(s)
    year, day = digits[:4], digits[4:8]
    tlr = list(reversed(day)) + year
    i2_1 = sum_s(sum_s(tlr[0], tlr[1]), sum_s(tlr[2], tlr[3]))
    i2_2 = sum_s(sum_s(tlr[4], tlr[5]), sum_ss(tlr[6], tlr[7]))
    core = sum_s(i2_1, i2_2)
    return i2_1 * 100 + i2_2 * 10 + core
