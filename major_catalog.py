# major_catalog.py — 教育部本科专业目录（2026）解析与加载
import json
import os
import re

_BASE = os.path.dirname(os.path.abspath(__file__))
_CATALOG_JSON = os.path.join(_BASE, 'data', 'major_catalog_2026.json')
_CATALOG_XLSX = os.path.join(_BASE, 'data', 'major_catalog_2026.xlsx')

_DISC_RE = re.compile(r'学科门类[：:]\s*(.+)')
_CODE_NAME_RE = re.compile(r'^(\d+[A-Z0-9]*)\s*(.+)$')
_CODE_ONLY_RE = re.compile(r'^\d+[A-Z0-9]*$')
_MAJOR_NOTE_RE = re.compile(r'（注：[^）]*）')


def _clean_major_label(text):
    """去掉括号内说明及原专业代码，仅保留专业名称。"""
    s = re.sub(r'[\r\n\s]+', '', str(text or '').strip())
    s = _MAJOR_NOTE_RE.sub('', s)
    s = re.sub(r'原专业代码为[^。）]*[。]?', '', s)
    return s.strip()


def _extract_codes_from_a(a):
    return [
        ln.strip()
        for ln in str(a or '').split('\n')
        if _CODE_ONLY_RE.match(ln.strip())
    ]


def _extract_major_names_from_blob(label):
    s = re.sub(r'[\r\n\s]+', '', str(label or '').strip())
    if not s:
        return []
    parts = re.findall(r'([^（]+（注：[^）]*）)', s)
    if parts:
        return [n for n in (_clean_major_label(p) for p in parts) if n]
    cleaned = _clean_major_label(s)
    return [cleaned] if cleaned else []


def _try_parse_parallel_majors(a, label):
    """A 列多行代码 + D/C 列合并说明 → 拆成多条专业。"""
    codes = _extract_codes_from_a(a)
    if len(codes) < 2:
        return None
    names = _extract_major_names_from_blob(label)
    out = []
    for i, code in enumerate(codes):
        if i >= len(names):
            break
        out.append({'kind': 'major', 'code': code, 'name': names[i]})
    return out or None


def _ensure_cross_category(cur_disc, cur_cat):
    if cur_disc and cur_disc.get('id') == '14' and cur_cat is None:
        cur_cat = {'id': '1401', 'title': '交叉学科类', 'majors': []}
        cur_disc['categories'].append(cur_cat)
    return cur_cat


def _norm_cat_id(code):
    c = re.sub(r'\D', '', str(code or ''))
    if not c:
        return str(code)
    if len(c) <= 4:
        return c.zfill(4) if len(c) >= 3 else c.zfill(3)
    return c


def _parse_a_line(line):
    line = str(line or '').strip()
    if not line:
        return None
    dm = _DISC_RE.search(line)
    if dm:
        cm = re.match(r'^(\d{2})', line)
        return {
            'kind': 'discipline',
            'code': cm.group(1) if cm else '',
            'name': dm.group(1).strip(),
        }
    m = _CODE_NAME_RE.match(line)
    if not m:
        return None
    code, name = m.group(1).strip(), m.group(2).strip()
    if not name:
        return None
    digits = re.sub(r'\D', '', code)
    if name.endswith('类') and len(digits) <= 4:
        return {'kind': 'category', 'code': code, 'name': name}
    if len(digits) >= 6 or re.search(r'[A-Z]', code):
        return {'kind': 'major', 'code': code, 'name': name}
    if name.endswith('类'):
        return {'kind': 'category', 'code': code, 'name': name}
    return {'kind': 'major', 'code': code, 'name': name}


def _row_label(row):
    """专业名称可能在 D 列或 C 列（艺术学等区块为 C 列）。"""
    if not row:
        return ''
    for idx in (3, 2):
        if len(row) > idx and row[idx] is not None and str(row[idx]).strip():
            return str(row[idx]).strip()
    return ''


def _parse_row(a, label):
    a = str(a).strip() if a is not None else ''
    d = str(label).strip() if label is not None else ''

    parallel = _try_parse_parallel_majors(a, d) if a and d else None
    if parallel:
        return parallel

    out = []
    if d:
        if _DISC_RE.search(d):
            cm = re.match(r'^(\d{2})', a)
            out.append({
                'kind': 'discipline',
                'code': cm.group(1) if cm else '',
                'name': _DISC_RE.search(d).group(1).strip(),
            })
        elif a and _CODE_ONLY_RE.match(a) and d.endswith('类'):
            out.append({'kind': 'category', 'code': a, 'name': d})
        elif a:
            out.append({'kind': 'major', 'code': a, 'name': _clean_major_label(d)})
    elif a:
        for line in a.split('\n'):
            parsed = _parse_a_line(line)
            if parsed:
                if parsed['kind'] == 'major':
                    parsed['name'] = _clean_major_label(parsed['name'])
                out.append(parsed)
    return out


def build_catalog_from_xlsx(xlsx_path=None):
    """从 Excel 构建学科门类 → 类别 → 专业 三级结构。"""
    path = xlsx_path or _CATALOG_XLSX
    if not os.path.isfile(path):
        return []

    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    disciplines = []
    cur_disc = None
    cur_cat = None
    disc_seq = 0

    for row in ws.iter_rows(values_only=True):
        label = _row_label(row)
        items = _parse_row(row[0] if row else None, label)
        for it in items:
            if it['kind'] == 'discipline':
                disc_seq += 1
                code = it['code'] or f'{disc_seq:02d}'
                cur_disc = {'id': code, 'title': it['name'], 'categories': []}
                disciplines.append(cur_disc)
                cur_cat = None
                cur_cat = _ensure_cross_category(cur_disc, cur_cat)
            elif it['kind'] == 'category':
                if not cur_disc:
                    continue
                cid = _norm_cat_id(it['code'])
                cur_cat = {'id': cid, 'title': it['name'], 'majors': []}
                cur_disc['categories'].append(cur_cat)
            elif it['kind'] == 'major':
                if not cur_disc:
                    continue
                cur_cat = _ensure_cross_category(cur_disc, cur_cat)
                if not cur_cat:
                    prefix = re.sub(r'\D', '', it['code'])[:4]
                    cur_cat = {'id': prefix, 'title': f'其他（{prefix}）', 'majors': []}
                    cur_disc['categories'].append(cur_cat)
                mid = re.sub(r'\s+', '', str(it['code']))
                major_label = _clean_major_label(it['name'])
                if not major_label:
                    continue
                if not any(m['id'] == mid for m in cur_cat['majors']):
                    cur_cat['majors'].append({'id': mid, 'label': major_label})
    wb.close()

    for disc in disciplines:
        disc['categories'] = [c for c in disc['categories'] if c['majors']]
    return disciplines


def _enrich_disciplines(disciplines):
    for disc in disciplines:
        for cat in disc['categories']:
            cat['group_id'] = f"cat_{cat['id']}"
            cat['note_field'] = f"major_note_{cat['id']}"
            search_bits = [cat['title']]
            for major in cat['majors']:
                major['item_id'] = f"m_{major['id']}"
                search_bits.append(major['label'])
            cat['search_text'] = ' '.join(search_bits)
    return disciplines


def build_category_major_filter(category_titles=None, group_ids=None):
    """根据所选专业类（目录类别）构建筛选集合：类别名 + 类内专业名。"""
    titles = {str(t).strip() for t in (category_titles or []) if str(t).strip()}
    major_names = set(titles)
    id_to_title = {}
    for disc in load_major_disciplines():
        for cat in disc['categories']:
            gid = cat.get('group_id') or ''
            title = (cat.get('title') or '').strip()
            if gid:
                id_to_title[gid] = title
            if title in titles:
                for major in cat.get('majors') or []:
                    label = (major.get('label') or '').strip()
                    if label:
                        major_names.add(label)
    for gid in group_ids or []:
        title = id_to_title.get(str(gid).strip())
        if title:
            titles.add(title)
    if group_ids:
        for title in list(titles):
            for disc in load_major_disciplines():
                for cat in disc['categories']:
                    if (cat.get('title') or '').strip() != title:
                        continue
                    for major in cat.get('majors') or []:
                        label = (major.get('label') or '').strip()
                        if label:
                            major_names.add(label)
    return titles, major_names


def load_major_disciplines():
    """加载本科专业目录（优先 JSON，缺失时从 xlsx 生成）。"""
    if os.path.isfile(_CATALOG_JSON):
        with open(_CATALOG_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        disciplines = data.get('disciplines') or []
    elif os.path.isfile(_CATALOG_XLSX):
        disciplines = build_catalog_from_xlsx()
    else:
        return []

    return _enrich_disciplines(disciplines)
