# jilin_2025_enrollment_loader.py — 吉林省 2025 招生计划 Excel → JSON
"""解析《吉林省普通高考分科类分专业招生计划》xlsx，输出 JSON。"""
import json
import os
import re

_BASE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_XLSX = os.path.join(_BASE, 'data', 'college_major_scores', '吉林省_2025招生计划.xlsx')
_DEFAULT_JSON = os.path.join(_BASE, 'data', 'college_major_scores', '吉林省_2025招生计划.json')
_DEFAULT_JSON_SPORT_ART = os.path.join(
    _BASE, 'data', 'college_major_scores', '吉林省_2025招生计划_体育艺术类.json',
)

# 普通类数据区（1-based 行号）
_HIST_START = 87
_PHYS_MARKER = 5582
_PHYS_START = 5583
_MAIN_END = 17404

# 体育 / 艺术数据区
_SPORT_ART_START = 17405
_SPORT_ART_END = 20202

_SPECIAL_CATEGORIES = (
    '历史体育类', '物理体育类', '历史艺术类', '物理艺术类',
)

_RE_SCHOOL = re.compile(
    r'^(\d{3,5})\s+(.+?)(?:[\(（].*[\)）])?\s*$'
)
_RE_GROUP = re.compile(r'^第\s*\d+\s*组')
_RE_BATCH = re.compile(
    r'(普通)?(提前批\s*[AB]段|提前批\s*A\s*段|本科批|专科批|提前批\s*B\s*段)'
)
_RE_RESELECT = re.compile(r'再选\s*科\s*目\s*[:：]\s*([^)）\n]+)')
_RE_RESELECT_BLOCK = re.compile(
    r'[（(][^（)）]*?再选[^（)）]*?科\s*目[^（)）]*?[）)]',
)
_RE_GENDER_BLOCK = re.compile(
    r'[（(][^（)）]*?只\s*招\s*(?:男|女)\s*生[^（)）]*?[）)]',
)
_RE_EMPLOY_BLOCK = re.compile(
    r'[（(][^（)）]*?面向[^（)）]*?就\s*业[^（)）]*?[）)]',
)
_RE_EMPLOY_INLINE = re.compile(r'面向\s*.+?就\s*业')

_SUBJECT_KEYS = ('思想政治', '化学', '生物', '地理', '物理', '历史')


def _cell_str(val):
    if val is None:
        return ''
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return re.sub(r'\s+', ' ', str(val).strip())


def _norm_text_spaces(text):
    """去掉汉字之间、中文标点周围的无效空格。"""
    s = (text or '').strip()
    if not s:
        return ''
    s = re.sub(r'\s+', ' ', s)
    while True:
        ns = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', s)
        if ns == s:
            break
        s = ns
    s = re.sub(r'([\u4e00-\u9fff])\s+([，。；：、）])', r'\1\2', s)
    s = re.sub(r'([（(，。；：、])\s+([\u4e00-\u9fff])', r'\1\2', s)
    s = re.sub(r'\(\s+', '(', s)
    s = re.sub(r'\s+\)', ')', s)
    s = re.sub(r'（\s+', '（', s)
    s = re.sub(r'\s+）', '）', s)
    s = re.sub(r'[,，]\s*[,，]+', '，', s)
    return s.strip()


def _norm_entity_name(name):
    """院校/专业名：合并汉字间误插空格。"""
    return _norm_text_spaces(name)


def _cell_num(val):
    if val is None or str(val).strip() == '':
        return None
    try:
        n = float(val)
        return int(n) if n == int(n) else n
    except (TypeError, ValueError):
        return None


def _norm_batch(text):
    t = re.sub(r'\s+', '', text or '')
    if '提前批' in t and 'A' in t:
        return '提前A'
    if '提前批' in t and 'B' in t:
        return '提前B'
    if '专科' in t:
        return '专科'
    if '本科' in t:
        return '本科'
    return ''


def _parse_reselect(note):
    note = note or ''
    if not note.strip():
        return '不限'
    if '不限' in note and '再选' not in note:
        return '不限'
    m = _RE_RESELECT.search(note)
    if m:
        raw = m.group(1)
        found = [s for s in _SUBJECT_KEYS if s in raw.replace(' ', '')]
        if found:
            return '/'.join(found)
        cleaned = re.sub(r'\s+', '', raw)
        return cleaned or '不限'
    if '再选' in note:
        found = [s for s in _SUBJECT_KEYS if s in note]
        if found:
            return '/'.join(found)
    return '不限'


def _note_compact(note):
    return re.sub(r'\s+', '', note or '')


def _parse_gender(note):
    """招生性别：只招男生 / 只招女生 / 暂无。"""
    c = _note_compact(note)
    if '只招男生' in c:
        return '只招男生'
    if '只招女生' in c:
        return '只招女生'
    return '暂无'


def _parse_enrollment_remark(note):
    """招生备注：面向……就业 / 暂无。"""
    c = _note_compact(note)
    m = re.search(r'(面向.+?就业)', c)
    if m:
        return m.group(1)
    return '暂无'


def _clean_major_note(note_raw):
    """专业备注：去掉再选选科、招生性别、面向就业等已单独拆出的内容。"""
    note = (note_raw or '').strip()
    if not note:
        return ''

    kept = []
    for m in re.finditer(r'[（(]([^（)）]+)[）)]', note):
        seg = m.group(1)
        compact = _note_compact(seg)
        if not compact:
            continue
        if '再选' in compact and '科目' in compact:
            continue
        if compact in ('不限',) and '再选' in seg:
            continue
        if '只招男生' in compact or '只招女生' in compact:
            continue
        if '面向' in compact and '就业' in compact:
            rest = _RE_EMPLOY_INLINE.sub('', seg)
            rest = re.sub(r'\s+', ' ', rest).strip(' ,、；;，。')
            rest = re.sub(r'[,，]\s*[,，]+', '，', rest)
            if rest and _note_compact(rest):
                kept.append(_norm_text_spaces(rest))
            continue
        kept.append(_norm_text_spaces(seg))

    if kept:
        return _finalize_major_note(' '.join(f'({p})' for p in kept))

    cleaned = _RE_RESELECT_BLOCK.sub('', note)
    cleaned = _RE_GENDER_BLOCK.sub('', cleaned)
    cleaned = _RE_EMPLOY_BLOCK.sub('', cleaned)
    cleaned = _RE_EMPLOY_INLINE.sub('', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,、；;，。')
    cleaned = re.sub(r'[,，]\s*[,，]+', '，', cleaned)
    return _finalize_major_note(cleaned)


def _finalize_major_note(parts_joined):
    """合并括号片段并去掉空备注、无效空格。"""
    if not parts_joined:
        return ''
    return _norm_text_spaces(parts_joined)


def _looks_like_note_only(text):
    t = (text or '').strip()
    if not t:
        return True
    if t.startswith('(') or t.startswith('（'):
        if '再选' in t[:120] or '科目' in t[:40]:
            return True
    return False


def _extract_major_name(name_raw, note_raw):
    """专业名优先取「院校专业组及专业名称」列；否则从备注括号中提取。"""
    name = _cell_str(name_raw)
    note = _cell_str(note_raw)

    if name and not _looks_like_note_only(name):
        if not (name.startswith('(') and '再选' in name):
            return _norm_entity_name(name)

    candidates = []
    for m in re.finditer(r'[（(]([^（)）]+)[）)]', note):
        seg = m.group(1)
        compact = re.sub(r'\s+', '', seg)
        if not compact or len(compact) < 2:
            continue
        if '再选' in compact or '科目' in compact:
            continue
        if compact.startswith('根据') or '招生章程' in compact:
            continue
        if compact in ('不限', '只招男生', '只招女生', '只招英语考生'):
            continue
        candidates.append(_norm_text_spaces(seg))

    if not candidates:
        return ''

    # 取备注中第一个像专业名的括号片段（如「法语」「马克思主义理论」）
    for c in candidates:
        if 2 <= len(c) <= 24:
            return _norm_entity_name(c)
    return _norm_entity_name(candidates[0])


def _parse_special_category(cells):
    for c in (cells or [])[:8]:
        s = re.sub(r'\s+', '', _cell_str(c))
        if s in _SPECIAL_CATEGORIES:
            return s
    return None


def _is_general_category_marker(c0):
    s = re.sub(r'\s+', '', c0)
    return s in ('历史类', '物理类')


def _is_section_title(c0):
    if not c0:
        return False
    if c0 == '代号' or c0.startswith('代号'):
        return False
    if '录取院校' in c0 or ('招生计划' in c0 and '2025' in c0):
        return True
    if _norm_batch(c0):
        return True
    return False


def _detect_layout(row):
    """根据表头行检测左右栏列索引（以「代号」列为分栏边界）。"""
    cells = [_cell_str(c) for c in row]
    code_cols = [
        i for i, c in enumerate(cells[:40])
        if re.sub(r'\s+', '', c) == '代号'
    ]
    if not code_cols:
        return []

    def find_block(start_idx, end_idx):
        code_i = name_i = dur_i = plan_i = note_i = None
        for i in range(start_idx, end_idx):
            lab = re.sub(r'\s+', '', cells[i])
            if lab == '代号' and code_i is None:
                code_i = i
            if ('院校专业' in lab and '备注' not in lab and '再选' not in lab) or lab == '院校专业组及专业名称':
                name_i = i
            if '学制' in lab or lab == '学制/年':
                dur_i = i
            if lab == '计划数':
                plan_i = i
            if '再选' in lab or '专业备注' in lab:
                note_i = i
        if code_i is not None and name_i is not None:
            return {
                'code': code_i,
                'name': name_i,
                'duration': dur_i,
                'plan': plan_i,
                'note': note_i,
            }
        return None

    layouts = []
    for bi, start in enumerate(code_cols[:2]):
        end = code_cols[bi + 1] if bi + 1 < len(code_cols) else min(start + 16, len(cells))
        block = find_block(start, end)
        if block:
            layouts.append(block)
    return layouts


def _parse_school_line(text):
    text = _cell_str(text)
    if not text:
        return None
    m = _RE_SCHOOL.match(text)
    if m:
        return m.group(2).strip()
    if re.search(r'(大学|学院|专科学校|职业学院|职业技术)', text) and re.match(r'^\d', text):
        parts = text.split(None, 1)
        if len(parts) >= 2:
            return parts[1].split('(')[0].split('（')[0].strip()
    return None


def _is_major_row(layout, row, school):
    if not school:
        return False
    name = _cell_str(row[layout['name']] if layout['name'] < len(row) else '')
    if not name or _RE_GROUP.match(name):
        return False
    if _parse_school_line(name):
        return False
    plan = layout.get('plan')
    dur = layout.get('duration')
    plan_v = _cell_num(row[plan]) if plan is not None and plan < len(row) else None
    dur_v = _cell_num(row[dur]) if dur is not None and dur < len(row) else None
    if plan_v is not None and plan_v > 0:
        return True
    if dur_v is not None and dur_v > 0 and re.match(r'^\d+$', name) is None:
        if not re.match(r'^\d{4,}', name):
            return True
    code = _cell_str(row[layout['code']] if layout['code'] < len(row) else '')
    if code and name and not _RE_GROUP.match(name):
        if re.match(r'^\d+$', code) or re.match(r'^\d{3,}', code + name):
            if plan_v is not None or dur_v is not None:
                return True
    return False


def _extract_major_code(row, layout):
    """专业行前数字代号（如 001、026），用于区分同校同专业不同方向。"""
    code_col = layout['code']
    for off in (0, 1):
        i = code_col + off
        if i >= len(row):
            continue
        raw = _cell_str(row[i])
        compact = re.sub(r'\s+', '', raw)
        if re.match(r'^\d{1,3}$', compact):
            return compact.zfill(3)
    return ''


def _emit_record(records, category, batch, school, row, layout):
    dur_i, plan_i, note_i = layout.get('duration'), layout.get('plan'), layout.get('note')
    name_raw = row[layout['name']] if layout['name'] < len(row) else ''
    note_raw = row[note_i] if note_i is not None and note_i < len(row) else ''
    major = _extract_major_name(name_raw, note_raw)
    if not major or _RE_GROUP.match(major):
        return
    duration = _cell_str(row[dur_i]) if dur_i is not None and dur_i < len(row) else ''
    plan = _cell_num(row[plan_i]) if plan_i is not None and plan_i < len(row) else None
    note_text = _cell_str(note_raw)
    if plan is None and not note_text and not duration:
        return
    reselect = _parse_reselect(note_text)
    gender = _parse_gender(note_text)
    enroll_remark = _parse_enrollment_remark(note_text)
    records.append({
        '大学': _norm_entity_name(school),
        '专业代号': _extract_major_code(row, layout),
        '专业': _norm_entity_name(major),
        '批次': _norm_text_spaces(batch),
        '类别': _norm_text_spaces(category),
        '学制': _norm_text_spaces(duration or ''),
        '招生人数': plan if plan is not None else '',
        '再选选科要求': _norm_text_spaces(reselect),
        '招生性别': _norm_text_spaces(gender),
        '招生备注': _norm_text_spaces(enroll_remark),
        '专业备注': _clean_major_note(note_text),
    })


def _school_code_prefix(text):
    """院校行代号前缀，如 2203 长春理工大学 → 2203。"""
    text = _cell_str(text)
    m = re.match(r'^(\d{4})', text)
    return m.group(1) if m else ''


def _bind_right_to_left_school(schools_state):
    """省内院校（22xx）左栏出现后，同行右栏专业归左栏院校。"""
    if not schools_state.get('left'):
        return None
    prefix = schools_state.get('left_code') or ''
    if prefix.startswith('22'):
        return schools_state['left']
    return None


def _new_schools_state():
    return {'left': None, 'right': None, 'stream': None, 'left_code': ''}


def _left_row_has_major_or_group(row, layout):
    """左栏该行是否为专业行或专业组行（不含单独院校行）。"""
    name_col = layout['name']
    name_text = _cell_str(row[name_col] if name_col < len(row) else '')
    if not name_text:
        return False
    if _parse_school_line(name_text):
        return False
    if _RE_GROUP.match(name_text):
        return True
    return _is_major_row(layout, row, True)


def _process_layout_row(records, category, batch, schools_state, side, row, layout, bind_school=None):
    """处理单行中某一栏（左或右）。bind_school 用于同行右栏挂靠左栏院校。"""
    code_col = layout['code']
    code_text = _cell_str(row[code_col] if code_col < len(row) else '')
    name_col = layout['name']
    name_text = _cell_str(row[name_col] if name_col < len(row) else '')

    sch = _parse_school_line(code_text) or _parse_school_line(name_text)
    if sch:
        schools_state[side] = _norm_entity_name(sch)
        if side == 'left':
            schools_state['left_code'] = _school_code_prefix(code_text or name_text)
        return
    school = bind_school if bind_school else schools_state.get(side)
    if _is_major_row(layout, row, school):
        _emit_record(records, category, batch, school, row, layout)


def _process_page_rows(records, category, batch, layouts, page_rows, schools_state):
    """双栏：先读完本页左栏，再读右栏；22xx 省内院校同行右栏专业挂靠左栏。"""
    if not layouts:
        return
    left = layouts[0]
    stream = schools_state.get('stream')
    if stream:
        schools_state['left'] = stream

    for row in page_rows:
        _process_layout_row(records, category, batch, schools_state, 'left', row, left)

    if len(layouts) > 1:
        right = layouts[1]
        if stream:
            schools_state['right'] = stream
        elif schools_state['right'] is None and schools_state['left']:
            schools_state['right'] = schools_state['left']
        for row in page_rows:
            bind = None
            if _left_row_has_major_or_group(row, left):
                bind = _bind_right_to_left_school(schools_state)
            _process_layout_row(
                records, category, batch, schools_state, 'right', row, right, bind_school=bind,
            )
        schools_state['stream'] = schools_state['right'] or schools_state['left']
    else:
        schools_state['stream'] = schools_state['left']


def _parse_rows(ws, row_start, row_end, mode='general'):
    """mode: general | sport_art"""
    records = []
    category = '历史类' if mode == 'general' else '历史体育类'
    batch = ''
    layouts = []
    page_rows = []
    schools_state = _new_schools_state()

    def _flush_page():
        nonlocal page_rows
        if page_rows and layouts and batch:
            _process_page_rows(records, category, batch, layouts, page_rows, schools_state)
        page_rows = []

    def _reset_schools():
        nonlocal schools_state
        schools_state = _new_schools_state()

    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if i < row_start or i > row_end:
            continue

        cells = list(row) if row else []
        c0 = _cell_str(cells[0] if cells else '')

        if mode == 'general':
            if i == _PHYS_MARKER:
                _flush_page()
                category = '物理类'
                layouts = []
                _reset_schools()
                continue
            if i >= _PHYS_START:
                category = '物理类'
            else:
                category = '历史类'
            if _is_general_category_marker(c0):
                _flush_page()
                layouts = []
                _reset_schools()
                continue
        else:
            special = _parse_special_category(cells)
            if special:
                _flush_page()
                category = special
                layouts = []
                _reset_schools()
                continue

        if any(re.sub(r'\s+', '', _cell_str(c)) == '代号' for c in cells[:35]):
            _flush_page()
            layouts = _detect_layout(cells)
            continue

        batch_hit = ''
        for c in cells[:35]:
            s = _cell_str(c)
            if '录取院校' not in s:
                continue
            nb = _norm_batch(s)
            if nb:
                batch_hit = nb
                break
        if batch_hit:
            _flush_page()
            batch = batch_hit
            _reset_schools()
            continue

        if not layouts or not batch:
            continue

        page_rows.append(cells)

    _flush_page()
    return records


def parse_enrollment_xlsx(xlsx_path, mode='general'):
    import openpyxl

    if not os.path.isfile(xlsx_path):
        raise FileNotFoundError(xlsx_path)

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    if mode == 'sport_art':
        records = _parse_rows(ws, _SPORT_ART_START, _SPORT_ART_END, mode='sport_art')
    else:
        records = _parse_rows(ws, _HIST_START, _MAIN_END, mode='general')
    wb.close()
    return records


def _write_payload(json_path, records, title, categories):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    payload = {
        'title': title,
        'province': '吉林',
        'year': 2025,
        'categories': categories,
        'count': len(records),
        'records': records,
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def build_json(xlsx_path=None, json_path=None):
    xlsx_path = xlsx_path or _DEFAULT_XLSX
    json_path = json_path or _DEFAULT_JSON
    records = parse_enrollment_xlsx(xlsx_path, mode='general')
    return _write_payload(
        json_path, records,
        '吉林省2025招生计划（历史类、物理类）',
        ['历史类', '物理类'],
    )


def build_sport_art_json(xlsx_path=None, json_path=None):
    xlsx_path = xlsx_path or _DEFAULT_XLSX
    json_path = json_path or _DEFAULT_JSON_SPORT_ART
    records = parse_enrollment_xlsx(xlsx_path, mode='sport_art')
    return _write_payload(
        json_path, records,
        '吉林省2025招生计划（体育类、艺术类）',
        list(_SPECIAL_CATEGORIES),
    )


if __name__ == '__main__':
    import sys
    cmd = 'all'
    src = None
    for arg in sys.argv[1:]:
        low = arg.lower()
        if low in ('all', 'general', '普通', 'sport_art', '体育艺术', '体育', '艺术'):
            cmd = 'sport_art' if low in ('sport_art', '体育艺术', '体育', '艺术') else (
                'general' if low in ('general', '普通') else 'all'
            )
        elif arg.endswith('.xlsx') or os.path.isfile(arg):
            src = arg
    src = src or _DEFAULT_XLSX
    if not os.path.isfile(_DEFAULT_XLSX) and src != _DEFAULT_XLSX and os.path.isfile(src):
        os.makedirs(os.path.dirname(_DEFAULT_XLSX), exist_ok=True)
        import shutil
        shutil.copy2(src, _DEFAULT_XLSX)
        src = _DEFAULT_XLSX

    if cmd in ('all', 'general', '普通'):
        data = build_json(src)
        print('普通类', data['count'], '->', _DEFAULT_JSON)
    if cmd in ('all', 'sport_art', '体育艺术', '体育', '艺术'):
        data = build_sport_art_json(src)
        from collections import Counter
        c = Counter(r['类别'] for r in data['records'])
        print('体育艺术类', data['count'], dict(c), '->', _DEFAULT_JSON_SPORT_ART)
