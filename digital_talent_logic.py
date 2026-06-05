# digital_talent_logic.py - 数字天赋解读（对齐小程序 lifecode.js）
from datetime import datetime
from personality_loader import load_personality_data, personality_ready

NO_DATA = '暂无数据'


def sum_s(num1, num2) -> int:
    s = int(num1 or 0) + int(num2 or 0)
    while s > 9:
        s = sum(int(c) for c in str(s))
    return 5 if s == 0 else s


def make_union_code(a, b) -> int:
    return a * 100 + b * 10 + sum_s(a, b)


def format_birth_number(year: int, month: int, day: int) -> str:
    return f'{year}{month:02d}{day:02d}'


def format_birth_display(year: int, month: int, day: int) -> str:
    return f'{year}-{month:02d}-{day:02d}'


def format_pyramid_date(birth_str: str) -> str:
    parts = birth_str.split('-')
    if len(parts) != 3:
        return ''
    y, m, d = parts[0], parts[1], parts[2]
    cc = y[:2] if len(y) >= 4 else ''
    yy = y[2:4] if len(y) >= 4 else y
    return f'{d} {m} {cc} {yy}'.strip()


def _lookup(data, mapping: str, key) -> str:
    bucket = data.get(mapping) if data else None
    if not isinstance(bucket, dict):
        return NO_DATA
    val = bucket.get(str(key))
    return val if val else NO_DATA


def count_digits(arr) -> dict:
    cnt = {i: 0 for i in range(1, 10)}
    for n in arr:
        d = int(n)
        if d > 9:
            d = d % 9 or 9
        if 1 <= d <= 9:
            cnt[d] += 1
    return cnt


def calc_personal_year(birth_str: str, data: dict) -> dict:
    parts = birth_str.split('-')
    if len(parts) != 3:
        return {'year': 0, 'ofeeling': NO_DATA, 'guide': NO_DATA, 'attention': NO_DATA}
    universe_year = datetime.now().year
    month = int(parts[1]) or 0
    day = int(parts[2]) or 0
    total = universe_year + month + day
    while total > 9:
        total = sum(int(c) for c in str(total))
    key = str(total)
    return {
        'year': total,
        'ofeeling': _lookup(data, 'Ofeeling', key),
        'guide': _lookup(data, 'Guide', key),
        'attention': _lookup(data, 'attention', key),
    }


def compute_missing_repeated(main_nums, supp_nums, data: dict) -> dict:
    mr = data.get('MissingRepeated') or {}
    count_main = count_digits(main_nums)
    count_supp = count_digits(supp_nums)
    max_in = max(count_main.values()) if main_nums else 0
    max_out = max(count_supp.values()) if supp_nums else 0

    stat_pyramid = []
    aux_pyramid = []
    for i in range(1, 10):
        key = str(i)
        item = mr.get(key)
        if not item:
            continue
        main_cnt = count_main[i]
        supp_cnt = count_supp[i]
        stat_pyramid.append({
            'num': i,
            'count_in': main_cnt,
            'count_out': supp_cnt,
            'total_text': f'{main_cnt}个{i} {supp_cnt}个{i}',
            'missing_inside': item.get('inside') or NO_DATA,
            'repeated': item.get('repeated') or NO_DATA,
            'is_max_count': main_cnt > 0 and main_cnt == max_in,
        })
        aux_pyramid.append({
            'num': i,
            'count_in': main_cnt,
            'count_out': supp_cnt,
            'total_text': f'{main_cnt}个{i} {supp_cnt}个{i}',
            'missing_outside': item.get('outside') or NO_DATA,
            'repeated': item.get('repeated') or NO_DATA,
            'is_max_count': supp_cnt > 0 and supp_cnt == max_out,
        })
    return {'stat_pyramid': stat_pyramid, 'aux_pyramid': aux_pyramid}


def extract_text_results(data, cp, supervisor_code, peripheral_number, family_code,
                         father_gene, mother_gene, mind_num, subconsciousness_code,
                         t1, t2, t3, f1, f2, f3, a1, a2, a3) -> dict:
    cpk = str(cp)

    def union_pair(code):
        ck = str(code)
        return {
            'simple': _lookup(data, 'Digital_union_code', ck),
            'detail': _lookup(data, 'Detailed_Digital_union_code', ck),
        }

    return {
        'positively': _lookup(data, 'Positively', cpk),
        'negatively': _lookup(data, 'Negatively', cpk),
        'class': _lookup(data, 'Class', cpk),
        'mind_number': _lookup(data, 'MindNumber', str(mind_num)),
        'peripheral_number_text': _lookup(data, 'Peripheral_number', str(peripheral_number)),
        'subconsciousness': _lookup(data, 'Subconsciousness_Code', str(subconsciousness_code)),
        'family_code_text': _lookup(data, 'Family_Code', str(family_code)),
        'father_gene_simple': _lookup(data, 'Digital_union_code', str(father_gene)),
        'father_gene_detail': _lookup(data, 'Detailed_Digital_union_code', str(father_gene)),
        'mother_gene_simple': _lookup(data, 'Digital_union_code', str(mother_gene)),
        'mother_gene_detail': _lookup(data, 'Detailed_Digital_union_code', str(mother_gene)),
        'supervisor_code_simple': _lookup(data, 'Digital_union_code', str(supervisor_code)),
        'supervisor_code_detail': _lookup(data, 'Detailed_Digital_union_code', str(supervisor_code)),
        'twenty_forty': {1: union_pair(t1), 2: union_pair(t2), 3: union_pair(t3)},
        'forty_sixty': {1: union_pair(f1), 2: union_pair(f2), 3: union_pair(f3)},
        'after_sixty': {1: union_pair(a1), 2: union_pair(a2), 3: union_pair(a3)},
        'personality_traits_1': _lookup(data, 'Personality_Traits_1', cpk),
        'personality_traits_2': _lookup(data, 'Personality_Traits_2', cpk),
        'personality_traits_3': _lookup(data, 'Personality_Traits_3', cpk),
        'do_teaching_secret_1': _lookup(data, 'Do_Teaching_Secret_1', cpk),
        'do_teaching_secret_2': _lookup(data, 'Do_Teaching_Secret_2', cpk),
        'do_teaching_secret_3': _lookup(data, 'Do_Teaching_Secret_3', cpk),
        'dont_teaching_secret_1': _lookup(data, 'Dont_Teaching_Secret_1', cpk),
        'dont_teaching_secret_2': _lookup(data, 'Dont_Teaching_Secret_2', cpk),
        'dont_teaching_secret_3': _lookup(data, 'Dont_Teaching_Secret_3', cpk),
        'ease_anxiety': [
            _lookup(data, f'Ease_Anxiety_{i}', cpk) for i in range(1, 8)
        ],
    }


def perform_calculation(year: int, month: int, day: int) -> dict:
    """完整生命密码计算"""
    data = load_personality_data()
    child_birth = format_birth_display(year, month, day)
    child_birth_number = format_birth_number(year, month, day)

    digits = list(child_birth_number)
    child_year_box = digits[:4]
    child_day_box = digits[4:8]
    child_reverse_day = list(reversed(child_day_box))
    child_tlr_box = [int(x) for x in child_reverse_day + child_year_box]

    i1_1 = sum_s(child_tlr_box[0], child_tlr_box[1])
    i1_2 = sum_s(child_tlr_box[2], child_tlr_box[3])
    i1_3 = sum_s(child_tlr_box[4], child_tlr_box[5])
    i1_4 = sum_s(child_tlr_box[6], child_tlr_box[7])
    i2_1 = sum_s(i1_1, i1_2)
    i2_2 = sum_s(i1_3, i1_4)
    core = sum_s(i2_1, i2_2)

    s1_1 = sum_s(i1_1, i2_1)
    s1_2 = sum_s(i1_2, i2_1)
    s1_3 = sum_s(i1_3, i2_2)
    s1_4 = sum_s(i1_4, i2_2)
    s2_1 = sum_s(s1_1, s1_2)
    s2_2 = sum_s(s1_3, s1_4)
    s3_1 = sum_s(core, i2_2)
    s3_2 = sum_s(core, i2_1)
    s4_1 = sum_s(s3_1, s3_2)
    aux_left = sum_s(core, i2_2)
    aux_right = sum_s(core, i2_1)
    aux_apex = sum_s(aux_left, aux_right)

    supervisor_code = make_union_code(i2_1, i2_2)
    peripheral_number = s2_1 * 100 + s2_2 * 10 + s4_1
    family_code = i1_2 * 10 + i1_3
    father_gene = make_union_code(i1_1, i1_2)
    mother_gene = make_union_code(i1_3, i1_4)
    mind_num = sum_s(core, core)
    subconsciousness_code = sum_s(int(i1_1) + int(i1_4), core)

    t1 = make_union_code(i1_1, i2_1)
    t2 = make_union_code(i1_2, i2_1)
    t3 = make_union_code(s1_1, s1_2)
    f1 = make_union_code(i2_2, core)
    f2 = make_union_code(i2_1, core)
    f3 = make_union_code(s3_1, s3_2)
    a1 = make_union_code(i1_3, i2_2)
    a2 = make_union_code(i1_4, i2_2)
    a3 = make_union_code(s1_3, s1_4)

    text_results = extract_text_results(
        data, core, supervisor_code, peripheral_number, family_code,
        father_gene, mother_gene, mind_num, subconsciousness_code,
        t1, t2, t3, f1, f2, f3, a1, a2, a3,
    )

    pyramid = {
        'tlr_box': child_tlr_box,
        'inverted1': [i1_1, i1_2, i1_3, i1_4],
        'inverted2': [i2_1, i2_2],
        'core': core,
        'supplementary1': [s1_1, s1_2, s1_3, s1_4],
        'supplementary2': [s2_1, s2_2],
        'supplementary3': [s3_1, s3_2],
        'supplementary4': s4_1,
        'aux_top_base': [aux_left, aux_right],
        'aux_top_apex': aux_apex,
    }

    union_code_list = [
        {'code': father_gene, 'simple': text_results['father_gene_simple']},
        {'code': supervisor_code, 'simple': text_results['supervisor_code_simple']},
        {'code': t2, 'simple': text_results['twenty_forty'][2]['simple']},
        {'code': f1, 'simple': text_results['forty_sixty'][1]['simple']},
        {'code': f3, 'simple': text_results['forty_sixty'][3]['simple']},
        {'code': a2, 'simple': text_results['after_sixty'][2]['simple']},
        {'code': a3, 'simple': text_results['after_sixty'][3]['simple']},
        {'code': t1, 'simple': text_results['twenty_forty'][1]['simple']},
        {'code': t3, 'simple': text_results['twenty_forty'][3]['simple']},
        {'code': f2, 'simple': text_results['forty_sixty'][2]['simple']},
        {'code': a1, 'simple': text_results['after_sixty'][1]['simple']},
        {'code': mother_gene, 'simple': text_results['mother_gene_simple']},
    ]

    union_detail_list = [
        {'category': '坐镇码', 'code': supervisor_code, 'detail': text_results['supervisor_code_detail']},
        {'category': '父亲基因', 'code': father_gene, 'detail': text_results['father_gene_detail']},
        {'category': '母亲基因', 'code': mother_gene, 'detail': text_results['mother_gene_detail']},
        {'category': '20-40岁', 'code': t1, 'detail': text_results['twenty_forty'][1]['detail']},
        {'category': '20-40岁', 'code': t2, 'detail': text_results['twenty_forty'][2]['detail']},
        {'category': '20-40岁', 'code': t3, 'detail': text_results['twenty_forty'][3]['detail']},
        {'category': '40-60岁', 'code': f1, 'detail': text_results['forty_sixty'][1]['detail']},
        {'category': '40-60岁', 'code': f2, 'detail': text_results['forty_sixty'][2]['detail']},
        {'category': '40-60岁', 'code': f3, 'detail': text_results['forty_sixty'][3]['detail']},
        {'category': '60岁以后', 'code': a1, 'detail': text_results['after_sixty'][1]['detail']},
        {'category': '60岁以后', 'code': a2, 'detail': text_results['after_sixty'][2]['detail']},
        {'category': '60岁以后', 'code': a3, 'detail': text_results['after_sixty'][3]['detail']},
    ]

    main_nums = [i1_1, i1_2, i1_3, i1_4, i2_1, i2_2, core]
    supp_nums = [s1_1, s1_2, s1_3, s1_4, s3_1, s3_2, aux_left, aux_right, aux_apex]
    missing_repeated = compute_missing_repeated(main_nums, supp_nums, data)
    personal_year = calc_personal_year(child_birth, data)

    return {
        'child_birth': child_birth,
        'child_birth_number': child_birth_number,
        'birth_display': f'{year}年{month}月{day}日',
        'pyramid_date_text': format_pyramid_date(child_birth),
        'child_core_personality': core,
        'supervisor_code': supervisor_code,
        'peripheral_number': peripheral_number,
        'family_code': family_code,
        'father_gene': father_gene,
        'mother_gene': mother_gene,
        'mind_num': mind_num,
        'subconsciousness_code': subconsciousness_code,
        'pyramid': pyramid,
        'text_results': text_results,
        'union_code_list': union_code_list,
        'union_detail_list': union_detail_list,
        'missing_repeated': missing_repeated,
        'personal_year': personal_year,
        'data_ready': personality_ready(),
        'calculate_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }


def build_report(year: int, month: int, day: int) -> dict:
    return perform_calculation(year, month, day)


def parse_birth_date(birth_str: str):
    if not birth_str:
        return None
    try:
        parts = birth_str.strip().split('-')
        if len(parts) != 3:
            return None
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        datetime(year, month, day)
        if year < 1900 or year > datetime.now().year:
            return None
        return year, month, day
    except (ValueError, TypeError):
        return None


def parse_birth_selectors(year_s, month_s, day_s):
    try:
        year, month, day = int(year_s), int(month_s), int(day_s)
        datetime(year, month, day)
        if year < 1900 or year > datetime.now().year:
            return None
        return year, month, day
    except (ValueError, TypeError):
        return None
