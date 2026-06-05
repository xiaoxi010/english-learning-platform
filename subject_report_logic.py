# subject_report_logic.py - 学科测评报告解析（对齐 subjectV20ReportHelpers.js）
from datetime import datetime

SUBJECT_ORDER = ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']
NINE_CHALKBOARD_ORDER = ['数学', '物理', '历史', '生物', '语文', '英语', '政治', '化学', '地理']
NINE_GRID_ORDER = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '政治', '地理']
THINKING_RADAR_AXIS_ORDER = ['学习方法', '执行力', '线性思维', '宏观思维', '发散思维']
ENGLISH_DETAIL_ORDER = ['听力', '完形填空', '阅读理解', '7选5', '语言运用', '英语写作']
ENGLISH_WRITING_KEYS = ['英语写作', '写作']
GRADE_ORDER = ['D', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+', 'S']
SCI_TRACK = {'数学', '物理', '化学', '生物'}


def grade_rank(g):
    i = GRADE_ORDER.index(str(g or '').strip())
    return i if i >= 0 else -1


def grade_cell_tone_class(grade):
    r = grade_rank(grade)
    if r < 0:
        return 'sub-cell--na'
    if r >= 7:
        return f'sub-cell--orange-{10 - r + 1}'
    if r >= 3:
        return f'sub-cell--blue-{6 - r + 1}'
    return f'sub-cell--gray-{2 - r + 1}'


def subject_track(name):
    return 'sci' if name in SCI_TRACK else 'arts'


def normalize_detail_items(subject_name, detail):
    raw = dict(detail) if detail else {}
    name = str(subject_name or '').strip()
    if name == '英语':
        writing = None
        for k in ENGLISH_WRITING_KEYS:
            if raw.get(k) not in (None, ''):
                writing = raw[k]
                break
        for k in ENGLISH_WRITING_KEYS:
            raw.pop(k, None)
        if writing is not None:
            raw['英语写作'] = writing
        labels, grades = [], []
        used = set()
        for key in ENGLISH_DETAIL_ORDER:
            if key in raw and key not in used:
                labels.append(key)
                grades.append(raw[key])
                used.add(key)
        for key in raw:
            if key not in used:
                labels.append(key)
                grades.append(raw[key])
        return labels, grades
    labels = list(raw.keys())
    return labels, [raw[k] for k in labels]


def build_subject_modules(学科数据):
    if not 学科数据 or not isinstance(学科数据, dict):
        return []
    out, seen = [], set()

    def add_name(name):
        if name in seen:
            return
        sub = 学科数据.get(name)
        if not sub or not isinstance(sub, dict):
            return
        seen.add(name)
        detail = sub.get('细项') or {}
        labels, grades = normalize_detail_items(name, detail)
        out.append({
            'name': name,
            'grade': sub.get('综合评级') or '—',
            'score': sub.get('综合评分'),
            'labels': labels,
            'grades': grades,
        })

    for name in SUBJECT_ORDER:
        add_name(name)
    for name in 学科数据:
        add_name(name)
    return out


def build_nine_chalkboard(subjects):
    m = {s['name']: s for s in subjects}
    return [{
        'name': n,
        'grade': (m[n]['grade'] if n in m else '—'),
        'track': subject_track(n),
        'tone_class': grade_cell_tone_class(m[n]['grade'] if n in m else ''),
    } for n in NINE_GRID_ORDER]


def build_nine_radar_chalkboard(subjects):
    m = {s['name']: s for s in subjects}
    return [{'name': n, 'grade': m[n]['grade'] if n in m else '—'} for n in NINE_CHALKBOARD_ORDER]


def first_non_empty(obj, keys):
    if not obj:
        return ''
    for k in keys:
        v = obj.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ''


def parse_ability_rating(obj):
    if not obj:
        return None
    ar = obj.get('能力评级')
    if not ar or not isinstance(ar, dict):
        return None
    thinking_grades = [
        ar.get('学习方法评级') or '—',
        ar.get('执行力评级'),
        ar.get('线性思维评级'),
        ar.get('宏观思维评级'),
        ar.get('发散思维评级'),
    ]
    thinking_grades = [str(g).strip() if g not in (None, '') else '—' for g in thinking_grades]
    return {
        'subject_literacy': str(ar.get('学科素养评级') or '').strip(),
        'learning_method': str(ar.get('学习方法评级') or '').strip(),
        'thinking_labels': THINKING_RADAR_AXIS_ORDER[:],
        'thinking_grades': thinking_grades,
    }


def extract_ability_rating(row, 学科数据):
    parsed = parse_ability_rating(row) or parse_ability_rating(学科数据)
    if not parsed:
        return {
            'subject_literacy': '',
            'learning_method': '',
            'thinking_labels': THINKING_RADAR_AXIS_ORDER[:],
            'thinking_grades': ['—'] * 5,
        }
    return parsed


def finalize_thinking_radar(ab):
    labels_map = {}
    for i, lab in enumerate(ab.get('thinking_labels') or []):
        key = str(lab).strip()
        if key and key != '学科素养' and i < len(ab.get('thinking_grades', [])):
            labels_map[key] = ab['thinking_grades'][i]
    grades = [labels_map.get(n, '—') for n in THINKING_RADAR_AXIS_ORDER]
    return {'thinking_labels': THINKING_RADAR_AXIS_ORDER[:], 'thinking_grades': grades}


ELEC_ORDER_KEYS = ['phy', 'chem', 'bio', 'his', 'pol', 'geo', 'tech']
ELEC_KEY_TO_CHAR = {
    'phy': '物', 'chem': '化', 'bio': '生', 'his': '历',
    'pol': '政', 'geo': '地', 'tech': '技',
}
ELEC_CHAR_TO_KEY = {'物': 'phy', '化': 'chem', '生': 'bio', '历': 'his', '史': 'his', '政': 'pol', '地': 'geo', '技': 'tech'}


def parse_birth_number(birth_str):
    import re
    from digital_talent_logic import parse_birth_date, format_birth_display

    s = re.sub(r'\D', '', str(birth_str or ''))
    if len(s) == 8:
        return s
    parsed = parse_birth_date(str(birth_str or '').strip())
    if not parsed:
        return ''
    return re.sub(r'\D', '', format_birth_display(*parsed))


def parse_elective_keys(subjects_str):
    keys = []
    for ch in str(subjects_str or '').strip():
        k = ELEC_CHAR_TO_KEY.get(ch)
        if k and k not in keys:
            keys.append(k)
    return keys


def build_elective_combo_prefix(keys):
    if len(keys) != 3:
        return None, None
    if 'phy' in keys:
        anchor = 'phy'
        section_key = '物理类选科'
    elif 'his' in keys:
        anchor = 'his'
        section_key = '历史类选科'
    else:
        return None, None
    others = [k for k in ELEC_ORDER_KEYS if k in keys and k != anchor]
    if len(others) != 2:
        return None, None
    prefix = (
        ELEC_KEY_TO_CHAR[anchor]
        + ELEC_KEY_TO_CHAR[others[0]]
        + ELEC_KEY_TO_CHAR[others[1]]
    )
    return section_key, prefix


def lookup_elective_comprehensive(birth_str, subjects_str):
    from subject_code import get_subject_code_from_birth
    from subject_loader import load_comprehensive_json, find_comprehensive_by_code

    birth_number = parse_birth_number(birth_str)
    keys = parse_elective_keys(subjects_str)
    empty = {
        'subject_code': '',
        'rating': None,
        'optimal_combo': None,
        'optimal_grade': None,
        'ready': False,
    }
    if len(birth_number) != 8:
        return {**empty, 'error': 'invalid_birth'}
    if len(keys) != 3:
        return {**empty, 'error': 'invalid_subjects'}

    code = get_subject_code_from_birth(birth_number)
    empty['subject_code'] = code
    comp_row = find_comprehensive_by_code(load_comprehensive_json(), code)
    if not comp_row:
        return {**empty, 'error': 'no_data'}

    comp = comp_row.get('综合能力数据')
    if not comp and (comp_row.get('基础素养') or comp_row.get('选科推荐')):
        comp = comp_row
    if not isinstance(comp, dict):
        return {**empty, 'error': 'no_data'}

    section_key, prefix = build_elective_combo_prefix(keys)
    rating = None
    if section_key and prefix:
        section = comp.get(section_key) or {}
        grade = section.get(f'{prefix}评级')
        if grade is not None and str(grade).strip():
            rating = str(grade).strip()

    rec = comp.get('选科推荐') or {}
    optimal_combo = str(rec.get('选科推荐') or '').strip() or None
    optimal_grade = str(rec.get('选科评级') or '').strip() or None

    return {
        'subject_code': code,
        'rating': rating,
        'optimal_combo': optimal_combo,
        'optimal_grade': optimal_grade,
        'ready': True,
    }


def parse_comprehensive_combo_rows(section):
    if not section:
        return []
    items = {}
    for k, v in section.items():
        if not (k.endswith('评测') or k.endswith('评分')):
            continue
        prefix = k.replace('评测', '').replace('评分', '')
        rk = f'{prefix}评级'
        if section.get(rk) is None:
            continue
        score, grade = v, section[rk]
        prev = items.get(prefix)
        if not prev or float(score or 0) > float(prev['score'] or 0):
            items[prefix] = {'label': prefix, 'score': score, 'grade': grade}
    return sorted(items.values(), key=lambda x: (-float(x['score'] or 0), grade_rank(x['grade'])))


def build_comprehensive_aggregate_ratings(comp):
    if not comp:
        return []
    base = comp.get('基础素养') or comp.get('基础素养')
    base_obj = base if isinstance(base, dict) else None

    def g(keys):
        for key in keys:
            if base_obj:
                v = first_non_empty(base_obj, [key])
                if v:
                    return v
            v = first_non_empty(comp, [key])
            if v:
                return v
        return '—'

    return [
        {'title': '语数外综合', 'grade': g(['语数外综合评级']), 'track': 'lang'},
        {'title': '理科综合', 'grade': g(['理科综合评级', '理科素养评级']), 'track': 'sci'},
        {'title': '文科综合', 'grade': g(['文科综合评级', '文科素养评级']), 'track': 'arts'},
        {'title': '全学科综测', 'grade': g(['全学科综合评级', '全学科综测评级']), 'track': 'all'},
    ]


def build_aggregate_ratings_from_ability_and_comp(row, comp):
    ar = (row or {}).get('能力评级')
    comp_list = build_comprehensive_aggregate_ratings(comp or {})
    comp_map = {x['title']: x['grade'] for x in comp_list}

    def pick(keys, title):
        g = first_non_empty(ar, keys)
        return g or comp_map.get(title, '—')

    return [
        {'title': '语数外综合', 'grade': pick(['语数外综合评级'], '语数外综合'), 'track': 'lang'},
        {'title': '理科综合', 'grade': pick(['理科综合评级', '理科素养评级'], '理科综合'), 'track': 'sci'},
        {'title': '文科综合', 'grade': pick(['文科综合评级', '文科素养评级'], '文科综合'), 'track': 'arts'},
        {'title': '全学科综测', 'grade': pick(['全学科综合评级', '全学科综测评级'], '全学科综测'), 'track': 'all'},
    ]


def build_aggregate_modules_from_row(row):
    defs = [
        ('语数外综合', 'lang', ['语数外综合']),
        ('理科综合', 'sci', ['理科综合']),
        ('文科综合', 'arts', ['文科综合']),
        ('全学科综测', 'all', ['全学科综测', '全学科综合']),
    ]
    reserved = {'学科码', '学科数据', '能力评级', '学习码'} | set(SUBJECT_ORDER)
    result = []
    for title, track, keys in defs:
        sub = None
        for k in keys:
            if isinstance(row.get(k), dict):
                sub = row[k]
                break
        if sub:
            detail = sub.get('细项') or {}
            labels = list(detail.keys())
            grades = [detail[k] for k in labels]
            grade = str(sub.get('综合评级') or '—').strip() or '—'
            result.append({'title': title, 'track': track, 'grade': grade, 'labels': labels, 'grades': grades})
        else:
            result.append({'title': title, 'track': track, 'grade': '—', 'labels': [], 'grades': []})
    if any(len(m['labels']) >= 3 for m in result):
        return result
    return result


def build_basic_literacy_groups(subjects):
    groups = [
        ('语数外综合', ['语文', '数学', '英语']),
        ('理科综合', ['数学', '物理', '化学', '生物']),
        ('文科综合', ['语文', '英语', '政治', '历史', '地理']),
        ('全学科综测', SUBJECT_ORDER[:]),
    ]
    m = {s['name']: s for s in subjects}
    out = []
    for title, names in groups:
        out.append({
            'title': title,
            'labels': names,
            'grades': [str(m.get(n, {}).get('grade', '—')) for n in names],
        })
    return out


def build_display_aggregate_modules(row, subjects, aggregate_ratings):
    json_mods = build_aggregate_modules_from_row(row)
    merged = build_basic_literacy_groups(subjects)
    rating_map = {r['title']: r['grade'] for r in (aggregate_ratings or [])}
    display = []
    for i, jm in enumerate(json_mods):
        mg = merged[i] if i < len(merged) else {'labels': [], 'grades': []}
        hero = jm['grade'] if jm['grade'] != '—' else rating_map.get(jm['title'], '—')
        use_json = len(jm['labels']) >= 3
        display.append({
            'title': jm['title'],
            'track': jm['track'],
            'grade': hero,
            'labels': jm['labels'] if use_json else mg['labels'],
            'grades': jm['grades'] if use_json else mg['grades'],
        })
    return display


def split_aggregate_modules(display_mods):
    top = next((m for m in display_mods if m['title'] == '全学科综测'), None)
    g = top['grade'] if top else '—'
    rest = [m for m in display_mods if m['title'] != '全学科综测']
    return g, rest


def build_full_subject_report(name, gender, birth_number, ability_row, comp_row):
    from subject_code import get_subject_code_from_birth, compute_supervisor_code

    code = get_subject_code_from_birth(birth_number)
    supervisor = compute_supervisor_code(birth_number)
    学科数据 = ability_row.get('学科数据')
    if not 学科数据 and (ability_row.get('语文') or ability_row.get('数学')):
        学科数据 = ability_row
    subjects = build_subject_modules(学科数据)
    nine_chalkboard = build_nine_chalkboard(subjects)
    nine_radar = build_nine_radar_chalkboard(subjects)

    ab = extract_ability_rating(ability_row, 学科数据)
    radar = finalize_thinking_radar(ab)
    comp_subject_literacy = ab['subject_literacy']
    comp_err = ''
    comp_ready = False
    comp_top = ''
    comp_combo = ''
    comp_physics = []
    comp_history = []
    aggregate_ratings = build_aggregate_ratings_from_ability_and_comp(ability_row, {})

    if comp_row:
        comp = comp_row.get('综合能力数据')
        if not comp and (comp_row.get('基础素养') or comp_row.get('选科推荐')):
            comp = comp_row
        if not isinstance(comp, dict):
            comp = {}
        rec = comp.get('选科推荐') or {}
        comp_top = str(rec.get('选科评级') or '').strip()
        comp_combo = str(rec.get('选科推荐') or '').strip()
        if not comp_subject_literacy:
            comp_subject_literacy = str(rec.get('学科素养') or '').strip()
        comp_physics = parse_comprehensive_combo_rows(comp.get('物理类选科') or {})
        comp_history = parse_comprehensive_combo_rows(comp.get('历史类选科') or {})
        aggregate_ratings = build_aggregate_ratings_from_ability_and_comp(ability_row, comp)
        comp_ready = True
    else:
        comp_err = f'暂无学科码「{code}」对应的综合能力数据（可选）'

    display_agg = build_display_aggregate_modules(ability_row, subjects, aggregate_ratings)
    all_grade, group_modules = split_aggregate_modules(display_agg)

    birth_str = f'{birth_number[:4]}-{birth_number[4:6]}-{birth_number[6:8]}'
    return {
        'name': name or '未填写',
        'gender': gender or '—',
        'birth_display': f'{birth_number[:4]}年{birth_number[4:6]}月{birth_number[6:8]}日',
        'birth_date': birth_str,
        'birth_number': birth_number,
        'subject_code': code,
        'supervisor_code': supervisor,
        'subjects': subjects,
        'nine_chalkboard': nine_chalkboard,
        'nine_radar': nine_radar,
        'subject_literacy': comp_subject_literacy or '—',
        'thinking_labels': radar['thinking_labels'],
        'thinking_grades': radar['thinking_grades'],
        'all_subject_grade': all_grade,
        'group_modules': group_modules,
        'comp_top_grade': comp_top,
        'comp_recommend_combo': comp_combo,
        'comp_physics_rows': comp_physics,
        'comp_history_rows': comp_history,
        'comp_ready': comp_ready,
        'comp_err': comp_err,
        'calculate_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
