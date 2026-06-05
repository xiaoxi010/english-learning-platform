# gaokao_expert_import.py — 各省专家版 Excel 表头识别与行解析（统一为吉林标准字段）
"""各省 Excel 列序不同，按表头标签映射到统一 EXPERT_FIELDS；支持计划类别与山东等模板。"""
from __future__ import annotations

from gaokao_jilin_data_loader import EXPERT_FIELDS, _cell_str, _norm_value

# 标准字段（与吉林省导出 JSON 一致；含可选计划类别）
EXPERT_FIELD_KEYS = [key for key, _label in EXPERT_FIELDS]

# 表头中文 -> 标准字段 key（含别名）
HEADER_LABEL_TO_KEY = {label: key for key, label in EXPERT_FIELDS}
HEADER_LABEL_TO_KEY['计划类别'] = 'plan_category'

HEADER_ALIASES = {
    '生源省份': '生源地',
    '生源省': '生源地',
    '院校代号': '院校代码',
    '学校代码': '院校代码',
    '学校名称': '院校名称',
    '专业组代号': '专业组代码',
    '选考科目要求': '选科要求',
    '选考要求': '选科要求',
    '计划数': '计划人数',
    '招生人数': '计划人数',
    '所在省份': '所在省',
    '省份': '所在省',
    '隶属': '隶属单位',
    '性质': '公私性质',
    '办学性质': '公私性质',
    '最低分位次': '最低位次',
    '最高分位次': '最高位次',
    '24专业组最低分': 'g2024_min_score',
    '24专业组最低位次': 'g2024_min_rank',
    '24专业组录取人数': 'g2024_enroll_count',
    '24专业最低分': 'm2024_min_score',
    '24专业最低位次': 'm2024_min_rank',
    '24专业录取人数': 'm2024_enroll_count',
    '23专业最低分': 'm2023_min_score',
    '23专业最低位次': 'm2023_min_rank',
    '23专业录取人数': 'm2023_enroll_count',
}

# 表头重复出现时按从左到右依次填入的字段
REPEATED_HEADER_SLOTS = {
    '专业组录取人数': ['g2025_enroll_count', 'g2024_enroll_count'],
    '专业组最低分': ['g2025_min_score', 'g2024_min_score'],
    '专业组最低位次': ['g2025_min_rank', 'g2024_min_rank'],
    '录取人数': ['m2025_enroll_count', 'm2024_enroll_count', 'm2023_enroll_count'],
    '最低分': ['m2025_min_score', 'm2024_min_score', 'm2023_min_score'],
    '最低位次': ['m2025_min_rank', 'm2024_min_rank', 'm2023_min_rank'],
    '最高分': ['m2025_max_score'],
    '最高位次': ['m2025_max_rank'],
}

# 山东省等宽表模板（表头行含「院校」而非「院校名称」）
SHANDONG_HEADER_MAP = {
    '省份': 'source_region',
    '年份': 'year',
    '院校': 'school_name',
    '院校代码': 'school_code',
    '专业': 'major_name',
    '专业代码': 'major_code',
    '专业类': 'major_category',
    '专业备注': 'major_note',
    '科目': 'category',
    '选科要求': 'subject_requirement',
    '类型': 'school_type',
    '批次': 'batch',
    '计划类别': 'plan_category',
    '计划人数': 'plan_count',
    '学制': 'duration',
    '学费': 'tuition',
}


def _normalize_header_label(label):
    label = _cell_str(label).replace(' ', '').replace('\n', '')
    if not label:
        return ''
    return HEADER_ALIASES.get(label, label)


def detect_sheet_template(rows):
    """识别专家版 sheet 模板。"""
    for row in rows[:12]:
        cells = [_cell_str(c) for c in (row or [])]
        joined = ' '.join(cells)
        if '院校名称' in joined:
            return 'standard'
        if '院校专业组代码' in joined or ('院校代码' in joined and '专业组' in joined):
            return 'standard'
    for row in rows[:12]:
        cells = [_cell_str(c) for c in (row or [])]
        joined = ' '.join(cells)
        if '院校' in joined and '专业' in joined and '批次' in joined and '院校名称' not in joined:
            return 'shandong'
    return 'unknown'


def find_header_row_index(rows, template):
    for i, row in enumerate(rows[:15]):
        cells = [_cell_str(c) for c in (row or [])]
        joined = ' '.join(cells)
        if template == 'shandong':
            if '院校' in joined and '批次' in joined:
                return i
        elif '院校名称' in joined or '院校代码' in joined:
            return i
    return 2


def build_column_map(headers, template='standard'):
    """
    表头单元格列表 -> {field_key: column_index}
    未出现的标准字段不在 map 中，解析时填空字符串。
    """
    column_map = {}
    if template == 'shandong':
        for idx, raw in enumerate(headers):
            label = _cell_str(raw).replace(' ', '')
            if not label:
                continue
            key = SHANDONG_HEADER_MAP.get(label)
            if key and key not in column_map:
                column_map[key] = idx
        return column_map

    slot_cursors = {label: 0 for label in REPEATED_HEADER_SLOTS}

    for idx, raw in enumerate(headers):
        label = _normalize_header_label(raw)
        if not label:
            continue

        if label in REPEATED_HEADER_SLOTS:
            slots = REPEATED_HEADER_SLOTS[label]
            cursor = slot_cursors[label]
            while cursor < len(slots) and slots[cursor] in column_map:
                cursor += 1
            if cursor < len(slots):
                column_map[slots[cursor]] = idx
                slot_cursors[label] = cursor + 1
            continue

        key = HEADER_LABEL_TO_KEY.get(label)
        if key and key not in column_map:
            column_map[key] = idx

    return column_map


def parse_expert_row(cells, column_map):
    """按列映射解析一行，输出与吉林省 JSON 相同 key 集合的记录。"""
    rec = {key: '' for key, _ in EXPERT_FIELDS}
    for key, col_idx in column_map.items():
        if key not in rec:
            continue
        val = cells[col_idx] if col_idx < len(cells) else None
        rec[key] = _norm_value(val)
    return rec


def parse_expert_sheet_rows(rows, province=''):
    """
    解析整个 sheet，返回 (records, meta)。
    meta: template, header_row, column_map labels, column_count
    """
    template = detect_sheet_template(rows)
    if template == 'unknown':
        return [], {
            'template': 'unknown',
            'header_row': None,
            'error': '无法识别表头格式',
        }

    header_idx = find_header_row_index(rows, template)
    headers = [_cell_str(c) for c in (rows[header_idx] or [])]
    column_map = build_column_map(headers, template)

    records = []
    for row in rows[header_idx + 1:]:
        if not row or not any(_cell_str(c) for c in row):
            continue
        cells = list(row)
        rec = parse_expert_row(cells, column_map)
        if province and not rec.get('source_region'):
            rec['source_region'] = province
        if not rec.get('school_name'):
            continue
        records.append(rec)

    header_labels = {}
    for key, idx in column_map.items():
        for k, label in EXPERT_FIELDS:
            if k == key:
                header_labels[key] = label
                break
        if key == 'plan_category':
            header_labels[key] = '计划类别'

    return records, {
        'template': template,
        'header_row': header_idx,
        'column_count': len(headers),
        'mapped_fields': len(column_map),
        'column_map': column_map,
        'header_labels': header_labels,
    }
