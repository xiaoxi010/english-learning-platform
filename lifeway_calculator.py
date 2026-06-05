# lifeway_calculator.py - 人生道路计算（对齐 miniprogram/utils/calculator.js）
from datetime import datetime

SHOW_NUM_BOX = {
    'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8, 'i': 9, 'j': 1,
    'k': 2, 'l': 3, 'm': 4, 'n': 5, 'o': 6, 'p': 7, 'q': 8, 'r': 9, 's': 1, 't': 2,
    'u': 3, 'v': 4, 'w': 5, 'x': 6, 'y': 7, 'z': 8,
}
INNER_NUM_BOX = {
    'a': 1, 'b': 0, 'c': 0, 'd': 0, 'e': 5, 'f': 0, 'g': 0, 'h': 0, 'i': 9, 'j': 0,
    'k': 0, 'l': 0, 'm': 0, 'n': 0, 'o': 6, 'p': 0, 'q': 0, 'r': 0, 's': 0, 't': 0,
    'u': 3, 'v': 0, 'w': 0, 'x': 0, 'y': 0, 'z': 0,
}
PERSONAL_NUM_BOX = {
    'a': 0, 'b': 2, 'c': 3, 'd': 4, 'e': 0, 'f': 6, 'g': 7, 'h': 8, 'i': 0, 'j': 1,
    'k': 2, 'l': 3, 'm': 4, 'n': 5, 'o': 0, 'p': 7, 'q': 8, 'r': 9, 's': 1, 't': 2,
    'u': 0, 'v': 4, 'w': 5, 'x': 6, 'y': 7, 'z': 8,
}


def check(num):
    if num >= 10:
        return num // 10 + (num % 10)
    return num


def check_zero(num):
    if num >= 10:
        return num // 10 + (num % 10)
    return 0


def check_abs(num):
    return -num if num < 0 else num


def format_num(first, second, third):
    if third != 0:
        return f'{first}/{second}/{third}'
    return f'{first}/{second}'


def calculate_life_way(usr_name_pinyin: str, usr_birth: str) -> dict:
    """usr_birth: YYYYMMDD 8位"""
    usr_name_box = list(usr_name_pinyin.lower())
    usr_birth_box = [int(c) for c in usr_birth]
    usr_year = usr_birth_box[:4]
    usr_month = usr_birth_box[4:6]
    usr_day = usr_birth_box[6:8]
    usr_year_rev = usr_day + usr_month + usr_year

    constraints_sum = sum(usr_year_rev[:4])
    constraints_num = check(constraints_sum // 10 + constraints_sum % 10)

    twice_high_box = usr_year_rev[:2] + usr_year_rev[4:8]
    twice_high_sum = sum(twice_high_box)
    twice_high_num = check(twice_high_sum // 10 + twice_high_sum % 10)

    third_high_sum = constraints_num + twice_high_num
    third_high_num = check(third_high_sum // 10 + third_high_sum % 10)

    forth_high_box = usr_year_rev[2:4] + usr_year_rev[4:8]
    forth_high_sum = sum(forth_high_box)
    forth_high_num = check(forth_high_sum // 10 + forth_high_sum % 10)

    first_cal = sum(usr_year_rev)
    second_cal = check(first_cal // 10 + first_cal % 10)
    third_cal = check(second_cal) if second_cal >= 10 else 0

    first_challenge_month = check(sum(usr_month))
    first_challenge_day = check(sum(usr_day))
    first_challenge = check_abs(first_challenge_month - first_challenge_day)

    second_challenge_year = check(sum(usr_year))
    second_challenge = check_abs(second_challenge_year - first_challenge_day)
    third_challenge = check_abs(first_challenge - second_challenge)
    forth_challenge = check_abs(second_challenge_year - first_challenge_month)

    first_cycle = check(sum(usr_month))
    second_cycle = first_challenge_day
    third_cycle = second_challenge_year

    show_num_arr = [SHOW_NUM_BOX.get(c, 0) for c in usr_name_box]
    show_first = sum(show_num_arr)
    show_second = check(show_first)
    show_third = check_zero(show_second)
    temp_cal_box = [show_first, show_second]
    if show_third != 0:
        temp_cal_box.append(show_third)

    inner_num_arr = [INNER_NUM_BOX.get(c, 0) for c in usr_name_box]
    inner_first = sum(inner_num_arr)
    inner_second = check(inner_first)
    inner_third = check_zero(inner_second)

    personal_num_arr = [PERSONAL_NUM_BOX.get(c, 0) for c in usr_name_box]
    personal_first = sum(personal_num_arr)
    personal_second = check(personal_first)
    personal_third = check_zero(personal_second)

    if first_cal < 10:
        temp_num = first_cal
    elif second_cal < 10:
        temp_num = second_cal
    else:
        temp_num = third_cal

    def matur(mat):
        return mat % 9 if mat > 9 else mat

    maturity_num = matur(temp_cal_box[-1] + temp_num)

    a = h = 0
    g = i_cnt = 0
    b = c = f = 0
    d = e = 0
    for sn in show_num_arr:
        if sn == SHOW_NUM_BOX['a']:
            a += 1
        elif sn == SHOW_NUM_BOX['h']:
            h += 1
        if sn == SHOW_NUM_BOX['g']:
            g += 1
        elif sn == SHOW_NUM_BOX['i']:
            i_cnt += 1
        if sn == SHOW_NUM_BOX['b']:
            b += 1
        elif sn == SHOW_NUM_BOX['c']:
            c += 1
        elif sn == SHOW_NUM_BOX['f']:
            f += 1
        if sn == SHOW_NUM_BOX['d']:
            d += 1
        elif sn == SHOW_NUM_BOX['e']:
            e += 1
    head_num = a + h
    intuition_num = g + i_cnt
    emotion_num = b + c + f
    body_num = d + e

    black_hole_box = []
    for s in (str(show_first), str(show_second)):
        black_hole_box.extend(list(s))
    if show_third:
        black_hole_box.append(str(show_third))
    for s in (str(inner_first), str(inner_second)):
        black_hole_box.extend(list(s))
    if show_third:
        black_hole_box.append(str(show_third))
    for s in (str(personal_first), str(personal_second)):
        black_hole_box.extend(list(s))
    if show_third:
        black_hole_box.append(str(show_third))
    for s in (str(first_cal), str(second_cal)):
        black_hole_box.extend(list(s))
    if third_cal:
        black_hole_box.append(str(third_cal))
    for n in (constraints_num, twice_high_num, third_high_num, forth_high_num,
              first_challenge, second_challenge, third_challenge, forth_challenge, maturity_num):
        black_hole_box.append(str(n))

    black_hole_nums = [int(x) for x in black_hole_box]
    black_hole_num = 0
    for num in range(1, 10):
        if num not in black_hole_nums:
            black_hole_num = num
            break

    now = datetime.now()
    current_year_sum = sum(int(c) for c in str(now.year))
    person_year_sum = current_year_sum + constraints_num
    person_year = person_year_sum // 10 + person_year_sum % 10

    life_part1_end = 36 - second_cal
    life_stages = {
        'stage1': {'range': f'0-{life_part1_end}', 'cycle': first_cycle,
                   'peak': constraints_num, 'challenge': first_challenge},
        'stage2': {'range': f'{life_part1_end + 1}-{life_part1_end + 9}', 'cycle': second_cycle,
                   'peak': twice_high_num, 'challenge': second_challenge},
        'stage3': {'range': f'{life_part1_end + 10}-{life_part1_end + 18}', 'cycle': second_cycle,
                   'peak': third_high_num, 'challenge': third_challenge},
        'stage4': {'range': f'{life_part1_end + 19}+', 'cycle': third_cycle,
                   'peak': forth_high_num, 'challenge': forth_challenge},
    }

    return {
        'pyramid': {
            'peak': {'top': forth_high_num, 'middle': third_high_num,
                     'bottom_left': constraints_num, 'bottom_right': twice_high_num},
            'challenge': {'top_left': first_challenge, 'top_right': second_challenge,
                          'middle': third_challenge, 'bottom': forth_challenge},
        },
        'name_chart': {
            'show_num': format_num(show_first, show_second, show_third),
            'inner_num': format_num(inner_first, inner_second, inner_third),
            'personal_num': format_num(personal_first, personal_second, personal_third),
            'maturity_num': maturity_num,
        },
        'life_path': {
            'value': format_num(first_cal, second_cal, third_cal),
            'first': first_cal, 'second': second_cal, 'third': third_cal,
        },
        'temperament': {
            'head': head_num, 'emotion': emotion_num,
            'body': body_num, 'intuition': intuition_num,
        },
        'black_hole': black_hole_num,
        'person_year': person_year,
        'life_stages': life_stages,
        'details': {
            'constraints_num': constraints_num,
            'twice_high_num': twice_high_num,
            'third_high_num': third_high_num,
            'forth_high_num': forth_high_num,
            'first_cal': first_cal,
            'second_cal': second_cal,
            'third_cal': third_cal,
            'first_challenge': first_challenge,
            'second_challenge': second_challenge,
            'third_challenge': third_challenge,
            'forth_challenge': forth_challenge,
            'first_cycle': first_cycle,
            'second_cycle': second_cycle,
            'third_cycle': third_cycle,
            'show_num': {'first': show_first, 'second': show_second, 'third': show_third},
            'inner_num': {'first': inner_first, 'second': inner_second, 'third': inner_third},
            'personal_num': {'first': personal_first, 'second': personal_second, 'third': personal_third},
            'maturity_num': maturity_num,
            'head_num': head_num,
            'emotion_num': emotion_num,
            'body_num': body_num,
            'intuition_num': intuition_num,
            'black_hole_num': black_hole_num,
            'person_year': person_year,
            'show_num_arr': show_num_arr,
            'inner_num_arr': inner_num_arr,
            'personal_num_arr': personal_num_arr,
        },
    }
