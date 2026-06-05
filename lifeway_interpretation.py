# lifeway_interpretation.py - 人生道路解读文案（对齐 database.js）
from lifeway_loader import load_lifeway_data
from lifeway_calculator import check, check_zero

NO_DATA = '暂无数据'


def _get():
    return load_lifeway_data()


def _lk(data, key, field):
    bucket = data.get(field) if data else None
    if not isinstance(bucket, dict):
        return NO_DATA
    return bucket.get(str(key)) or NO_DATA


def normalize_for_compare(s):
    return (s or '').strip().replace(' ', '').replace('，', ',')


def dedupe_adjacent_lines(lines, prev_line=''):
    prev_norm = normalize_for_compare(prev_line)
    result = []
    for i, line in enumerate(lines):
        cur = (line or '').strip()
        prev_cur = normalize_for_compare(lines[i - 1]) if i > 0 else prev_norm
        if normalize_for_compare(cur) != prev_cur:
            result.append(cur)
    return '\n'.join(result)


def to_single_digit(n):
    if not n:
        return ''
    x = abs(int(n))
    while x >= 10:
        x = x // 10 + x % 10
    return str(x)


def get_person_year_data(person_year):
    key = str(person_year)
    d = _get()
    return {
        'word': _lk(d, key, 'person_year_word'),
        'class': _lk(d, key, 'person_year_class'),
        'special': _lk(d, key, 'person_year_special'),
        'tag': _lk(d, key, 'person_year_tag'),
        'advice': _lk(d, key, 'person_year_advice'),
    }


def get_show_num_data(show_num_second, show_num_arr):
    key = str(show_num_second)
    d = _get()
    show_box = []
    if show_num_arr:
        first_cal = sum(show_num_arr)
        second_cal = check(first_cal)
        third_cal = check_zero(second_cal)
        show_box.extend(list(str(first_cal)))
        show_box.extend(list(str(second_cal)))
        if third_cal:
            show_box.append(str(third_cal))
    good_core_key = show_box[4] if len(show_box) > 4 else key
    good_core = _lk(d, good_core_key, 'show_num_good') if good_core_key != '0' else _lk(d, key, 'show_num_good')
    good_other_lines = []
    for k in show_box[:4]:
        if k and k != '0':
            txt = (_lk(d, k, 'show_num_good') or '').strip()
            if txt and txt != NO_DATA:
                good_other_lines.append(txt)
    index = len(show_box) - 1 if show_box else 0
    idx_key = show_box[index] if show_box else key
    return {
        'summary': _lk(d, key, 'show_num'),
        'good_core': good_core,
        'good_other': dedupe_adjacent_lines(good_other_lines, good_core),
        'bad': _lk(d, idx_key, 'show_num_bad'),
        'child_special': _lk(d, idx_key, 'show_num_child_special'),
        'child_interest': _lk(d, idx_key, 'show_num_child_interest'),
    }


def get_inner_num_data(inner_second, inner_num_arr):
    key = str(inner_second)
    d = _get()
    inner_box = []
    if inner_num_arr:
        first_cal = sum(inner_num_arr)
        second_cal = check(first_cal)
        third_cal = check_zero(second_cal)
        inner_box.extend(list(str(first_cal)))
        inner_box.extend(list(str(second_cal)))
        if third_cal:
            inner_box.append(str(third_cal))
    core_key = inner_box[-1] if inner_box else key
    return {
        'tag': _lk(d, key, 'inner_num_tag'),
        'core_special': _lk(d, core_key, 'inner_num_core_special'),
        'core_special_2': _lk(d, core_key, 'inner_num_core_special_2'),
        'core_detail': _lk(d, core_key, 'inner_core_special_detail'),
        'admire': _lk(d, core_key, 'inner_num_admire'),
        'admire_detail': _lk(d, core_key, 'inner_num_admire_detail'),
        'interaction': _lk(d, core_key, 'inner_num_interaction'),
        'interaction_detail': _lk(d, core_key, 'inner_num_interaction_detail'),
        'bottom_line': _lk(d, core_key, 'inner_num_interaction_bottom_line'),
        'bottom_line_detail': _lk(d, core_key, 'inner_num_interaction_bottom_line_detail'),
    }


def get_personal_num_data(personal_num_str, first, second, third):
    d = _get()
    p_num = f'{first}/{second}/{third}' if third else f'{first}/{second}'
    first_str = str(first or 0)
    tens = first_str[0] if len(first_str) >= 2 else ''
    ones = first_str[1] if len(first_str) >= 2 else (first_str[0] if first_str else '')
    last_num = third if third else second
    last_digit = to_single_digit(last_num)
    term1 = _lk(d, tens, 'person_special_detail_1') if tens else ''
    term2 = _lk(d, ones, 'person_special_detail_1') if ones else ''
    term3 = _lk(d, last_digit, 'person_special_detail_1') if last_digit else ''
    detail_bucket = d.get('person_special_detail_2') or {}
    return {
        'special': _lk(d, p_num, 'person_special') or _lk(d, personal_num_str, 'person_special'),
        'detail_items': [
            {'term': term1, 'detail': detail_bucket.get(term1, '') if term1 else ''},
            {'term': term2, 'detail': detail_bucket.get(term2, '') if term2 else ''},
            {'term': term3, 'detail': detail_bucket.get(term3, '') if term3 else ''},
        ],
    }


def get_cycle_num_data(cycle_num):
    key = str(cycle_num)
    d = _get()
    return {
        'environment': _lk(d, key, 'cycle_num_environment'),
        'summary': _lk(d, key, 'cycle_num_summary'),
    }


def get_first_cycle_data(first_cycle):
    key = str(first_cycle)
    d = _get()
    return {
        'num': _lk(d, key, 'first_cycle_num'),
        'environment': _lk(d, key, 'cycle_num_environment'),
    }


def get_body_num_data(body_num):
    key = str(body_num)
    d = _get()
    return {'summary': _lk(d, key, 'body_num_summary'), 'detail': _lk(d, key, 'body_num_detail')}


def get_emotion_num_data(emotion_num):
    key = str(emotion_num)
    d = _get()
    return {
        'summary': _lk(d, key, 'emotion_num_summary'),
        'detail': _lk(d, key, 'emotion_num_detail'),
        'health': _lk(d, key, 'emotion_num_health'),
    }


def get_head_num_data(head_num):
    key = str(head_num)
    d = _get()
    return {
        'summary': _lk(d, key, 'head_num_summary'),
        'money': _lk(d, key, 'head_num_summary_money'),
    }


def get_intuition_num_data(intuition_num):
    key = str(intuition_num)
    d = _get()
    return {'summary': _lk(d, key, 'intuition_num_summary')}


def get_life_path_data(life_path_num):
    key = str(life_path_num)
    d = _get()
    w1 = _lk(d, key, 'life_way_word_1')
    w2 = _lk(d, key, 'life_way_word_2')
    w3 = _lk(d, key, 'life_way_word_3')
    w4 = _lk(d, key, 'life_way_word_4')
    w5 = _lk(d, key, 'life_way_word_5')
    mean = d.get('life_way_word_mean') or {}
    return {
        'summary': _lk(d, key, 'life_way_summary'),
        'word1': w1, 'word2': w2, 'word3': w3, 'word4': w4, 'word5': w5,
        'word_mean1': mean.get(w1, '') if w1 != NO_DATA else '',
        'word_mean2': mean.get(w2, '') if w2 != NO_DATA else '',
        'word_mean3': mean.get(w3, '') if w3 != NO_DATA else '',
        'word_mean4': mean.get(w4, '') if w4 != NO_DATA else '',
        'word_mean5': mean.get(w5, '') if w5 != NO_DATA else '',
    }


def get_constraints_num_data(constraints_num):
    key = str(constraints_num)
    d = _get()
    b1 = _lk(d, key, 'break_constraints_summary_1')
    b2 = _lk(d, key, 'break_constraints_summary_2')
    b3 = _lk(d, key, 'break_constraints_summary_3')
    b4 = _lk(d, key, 'break_constraints_summary_4')
    break_detail = d.get('break_constraints_detail') or {}
    return {
        'energy_good': _lk(d, key, 'constraints_num_energy_good'),
        'energy_less': _lk(d, key, 'constraints_num_energy_less'),
        'energy_more': _lk(d, key, 'constraints_num_energy_more'),
        'model_summary': _lk(d, key, 'constraints_model_summary'),
        'model_detail': _lk(d, key, 'constraints_model_detail'),
        'break_summary1': b1,
        'break_detail_text': break_detail.get(b1, '') if b1 != NO_DATA else '',
        'less_reason_detail': d.get('constraints_num_energy_less_reason_detail') or {},
    }


def get_high_num_data(high_num):
    key = str(high_num)
    d = _get()
    return {
        'summary': _lk(d, key, 'high_num_summary'),
        'detail': _lk(d, key, 'high_num_detail'),
        'avoid_summary': _lk(d, key, 'high_num_avoid_summary'),
        'avoid_detail': _lk(d, key, 'high_num_avoid_detail'),
        'career_summary': _lk(d, key, 'high_num_career_summary'),
        'career_detail': _lk(d, key, 'high_num_career_detail'),
    }


def get_challenge_num_data(challenge_num):
    key = str(challenge_num)
    d = _get()
    return {
        'summary': _lk(d, key, 'challenge_num_summary'),
        'detail': _lk(d, key, 'challenge_num_detail'),
        'face_summary': _lk(d, key, 'challenge_num_face_summary'),
        'face_detail': _lk(d, key, 'challenge_num_face_detail'),
        'breakthrough_summary': _lk(d, key, 'challenge_num_breakthrough_summary'),
        'breakthrough_detail': _lk(d, key, 'challenge_num_breakthrough_detail'),
    }


def get_full_interpretation(result: dict) -> dict:
    d = result['details']
    pn = d['personal_num']
    return {
        'person_year': get_person_year_data(d['person_year']),
        'show_num': get_show_num_data(d['show_num']['second'], d['show_num_arr']),
        'inner_num': get_inner_num_data(d['inner_num']['second'], d['inner_num_arr']),
        'personal_num': get_personal_num_data(
            result['name_chart']['personal_num'],
            pn['first'], pn['second'], pn['third'],
        ),
        'life_path': get_life_path_data(d['second_cal']),
        'constraints': get_constraints_num_data(d['constraints_num']),
        'first_cycle': get_first_cycle_data(d['first_cycle']),
        'high_nums': {
            'first': get_high_num_data(d['constraints_num']),
            'second': get_high_num_data(d['twice_high_num']),
            'third': get_high_num_data(d['third_high_num']),
            'forth': get_high_num_data(d['forth_high_num']),
        },
        'challenge_nums': {
            'first': get_challenge_num_data(d['first_challenge']),
            'second': get_challenge_num_data(d['second_challenge']),
            'third': get_challenge_num_data(d['third_challenge']),
            'forth': get_challenge_num_data(d['forth_challenge']),
        },
        'temperament': {
            'head': get_head_num_data(d['head_num']),
            'emotion': get_emotion_num_data(d['emotion_num']),
            'body': get_body_num_data(d['body_num']),
            'intuition': get_intuition_num_data(d['intuition_num']),
        },
        'cycles': {
            'first': get_cycle_num_data(d['first_cycle']),
            'second': get_cycle_num_data(d['second_cycle']),
            'third': get_cycle_num_data(d['third_cycle']),
        },
    }
