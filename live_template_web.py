# live_template_web.py — 直播模板
import json
import os
import re

from flask import Blueprint, jsonify, render_template, request, url_for

from score_rank_loader import PROVINCE_LIST
from major_catalog import load_major_disciplines
from college_major_score_loader import dataset_status, list_schools, load_dataset, lookup_record, search_records
from jilin_enrollment_plan_loader import (
    DISPLAY_COLUMNS as ENROLLMENT_PLAN_COLUMNS,
    FILTER_OPTIONS as ENROLLMENT_PLAN_FILTER_OPTIONS,
    _FILTER_LABELS as ENROLLMENT_PLAN_FILTER_LABELS,
    dataset_status as enrollment_plan_status,
    get_filter_options as enrollment_plan_filter_options,
    list_schools as enrollment_plan_schools,
    search_records as enrollment_plan_search,
)
from subject_report_logic import lookup_elective_comprehensive
from subject_loader import comprehensive_ready

live_template_bp = Blueprint('live_template', __name__)

_BASE = os.path.dirname(os.path.abspath(__file__))
_GAOKAO_ROWS_PATH = os.path.join(_BASE, 'data', 'gaokao_career_rows.json')


def _load_gaokao_rows():
    if not os.path.isfile(_GAOKAO_ROWS_PATH):
        return []
    with open(_GAOKAO_ROWS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _early_school(sid, label, hint=''):
    return {'id': sid, 'label': label, 'hint': hint}


def _early_schools_layout(note_idx, sections, extra_row=None, extra_note_field='', extra_notice=''):
    """通用：多分区学校按钮 + 每区整行意向/备注。"""
    base = f'early_{note_idx}'
    built = []
    for sec in sections:
        key = sec['key']
        items = sec.get('schools') or [(n, '') for n in sec.get('names', [])]
        built.append({
            'title': sec['title'],
            'subtitle': sec.get('subtitle', ''),
            'schools': [
                _early_school(
                    f'{base}_{key}_{i + 1}',
                    entry[0] if isinstance(entry, (list, tuple)) else entry,
                    entry[1] if isinstance(entry, (list, tuple)) and len(entry) > 1 else '',
                )
                for i, entry in enumerate(items)
            ],
            'note_field': f'early_note_{note_idx}_{key}',
        })
    return {
        'layout': 'school_sections',
        'sections': built,
        'extra_row': extra_row or [],
        'extra_note_field': extra_note_field or '',
        'extra_notice': extra_notice or '',
    }


def _early_teacher_struct(note_idx):
    """免费师范生：国家公费6所 + 优师8所 + 补充说明。"""
    six = [
        '北京师范大学', '华东师范大学', '东北师范大学',
        '陕西师范大学', '华中师范大学', '西南大学',
    ]
    return _early_schools_layout(
        note_idx,
        sections=[
            {
                'key': 'gjjf',
                'title': '国家公费师范生',
                'subtitle': '教育部直属 6 所师范类院校（985/211）',
                'names': six,
            },
            {
                'key': 'ys',
                'title': '优师专项计划',
                'subtitle': '教育部直属 6 所 + 西北师范大学 + 天水师范学院（共 8 所）',
                'names': six + ['西北师范大学', '天水师范学院'],
            },
        ],
        extra_notice='请参考各省发布的通知',
    )


def _early_medical_struct(note_idx):
    """免费医学生：本科 / 专科两类。"""
    return _early_schools_layout(
        note_idx,
        sections=[
            {
                'key': 'ben',
                'title': '本科',
                'subtitle': '农村户籍（以当年招生简章为准）',
                'names': [
                    '兰州大学', '天津中医药大学', '中医药大学', '西北民族大学',
                    '河西学院', '医学院', '齐齐哈尔医学院', '佳木斯大学',
                ],
            },
            {
                'key': 'zhuan',
                'title': '专科',
                'subtitle': '',
                'names': ['河西学院', '医学院', '卫生职业学院'],
            },
        ],
    )


# 提前批：院校按钮分区配置（title 与 Excel A 列一致）
_EARLY_SCHOOL_CONFIGS = {
    '公安警校': {
        'desc': '点选意向院校；本科、专科分区填写意向/备注。年龄要求 16–22 周岁（以当年简章为准）。',
        'sections': [
            {
                'key': 'ben',
                'title': '本科',
                'subtitle': '',
                'names': [
                    '中国人民公安大学', '中国人民警察大学', '中国刑事警察学院',
                    '南京警察学院', '郑州警察学院', '吉林警察学院',
                ],
            },
            {
                'key': 'zhuan',
                'title': '专科',
                'subtitle': '专科批',
                'names': ['西藏警官高等专科学校'],
            },
        ],
    },
    '司法警校': {
        'desc': '点选意向院校，下方整行填写意向/备注。',
        'sections': [
            {
                'key': 'main',
                'title': '招生院校',
                'subtitle': '',
                'names': ['中央司法警官学院', '中南财经政法大学', '政法大学'],
            },
        ],
    },
    '五大官校': {
        'desc': '点选意向院校，下方整行填写意向/备注。',
        'sections': [
            {
                'key': 'main',
                'title': '招生院校',
                'subtitle': '',
                'names': [
                    '北京电子科技学院', '国际关系学院', '外交学院',
                    '上海海关学院', '中国消防救援学院',
                ],
            },
        ],
    },
    '军事院校': {
        'desc': '按层次点选意向院校，各分区下方整行填写意向/备注。',
        'sections': [
            {
                'key': '985',
                'title': '985',
                'subtitle': '',
                'names': ['国防科技大学'],
            },
            {
                'key': '211',
                'title': '211',
                'subtitle': '',
                'names': ['空军军医大学'],
            },
            {
                'key': 'pt',
                'title': '普通类',
                'subtitle': '',
                'names': [
                    '空军工程大学', '海军航空大学', '武警工程大学', '武警警官学院',
                    '空军预警学院', '陆军炮兵防空兵学院', '陆军勤务学院',
                    '战略支援部队航天工程大学', '陆军边海防学院',
                    '战略支援部队信息工程大学', '火箭军工程大学', '武警海警学院',
                    '武警特种警察学院', '空军航空大学', '陆军工程大学',
                ],
            },
        ],
    },
    '航海类': {
        'desc': '专业方向：航海技术、轮机工程。点选意向院校后填写意向/备注。',
        'sections': [
            {
                'key': 'main',
                'title': '招生院校',
                'subtitle': '航海技术、轮机工程',
                'names': [
                    '大连海事大学', '宁波大学', '上海海事大学', '浙江海洋大学',
                    '集美大学', '广东海洋大学', '广州航海学院', '渤海大学', '天津理工大学',
                ],
            },
        ],
    },
    '飞行技术': {
        'desc': '点选意向院校，下方整行填写意向/备注。',
        'sections': [
            {
                'key': 'main',
                'title': '招生院校',
                'subtitle': '',
                'names': ['空军航空大学', '海军航空大学', '中国民用航空飞行学院'],
            },
        ],
    },
    '综合评价': {
        'desc': '需提前参加学校校园开放日活动及面试（以各校简章为准）。点选院校后填写意向/备注。',
        'sections': [
            {
                'key': 'main',
                'title': '招生院校',
                'subtitle': '',
                'names': ['上海科技大学', '北京外国语大学'],
            },
        ],
    },
    '马克思主义理论类': {
        'desc': '点选意向院校，下方整行填写意向/备注。',
        'sections': [
            {
                'key': 'main',
                'title': '招生院校',
                'subtitle': '',
                'names': [
                    '北京大学', '清华大学', '四川大学', '同济大学', '西安交通大学',
                    '中国人民大学', '南开大学', '福建师范大学', '广西师范大学',
                    '江西师范大学', '新疆师范大学',
                ],
            },
        ],
    },
    '港澳台、中外合作院校': {
        'desc': '点选意向院校，下方整行填写意向/备注。',
        'sections': [
            {
                'key': 'main',
                'title': '招生院校',
                'subtitle': '',
                'names': [
                    '香港中文大学', '香港城市大学', '香港中文大学（深圳）', '上海纽约大学',
                ],
            },
        ],
    },
    '小语种': {
        'desc': '点选意向院校，下方整行填写意向/备注。',
        'sections': [
            {
                'key': 'main',
                'title': '招生院校',
                'subtitle': '',
                'names': ['西安外国语大学', '北京语言大学', '四川外国语大学'],
            },
        ],
    },
}


def _apply_early_school_config(item, idx):
    """为指定提前批条目附加学校按钮布局。"""
    cfg = _EARLY_SCHOOL_CONFIGS.get(item['title'])
    if cfg:
        item.update(_early_schools_layout(idx, cfg['sections']))
        if cfg.get('desc'):
            item['desc'] = cfg['desc']
        return True
    if item['title'] == '免费师范生':
        item.update(_early_teacher_struct(idx))
        item['desc'] = (
            '国家公费师范生与优师专项计划院校可点选；'
            '补充选项请参考各省发布的通知。'
        )
        return True
    if item['title'] == '免费医学生':
        item.update(_early_medical_struct(idx))
        item['desc'] = '分本科、专科两类，点选意向院校后在对应栏填写意向/备注。'
        return True
    return False


def _early_batch_policies(rows):
    """提前批大类：按钮选择 + 选中后展示说明与意向（与专业意向同模式）。"""
    out = []
    for row in rows:
        r = row.get('_r')
        if not (21 <= r <= 36):
            continue
        if row.get('A'):
            idx = len(out) + 1
            item = {
                'id': f'early_{idx}',
                'button_label': row['A'].strip(),
                'title': row['A'].strip(),
                'desc': row.get('C', '') or '',
                'note_field': f'early_note_{idx}',
                'layout': 'simple',
            }
            _apply_early_school_config(item, idx)
            out.append(item)
        elif row.get('C') and out and out[-1]['layout'] == 'simple':
            prev = out[-1]['desc']
            out[-1]['desc'] = (prev + '\n' + row['C']).strip() if prev else row['C']
    return out


def _strip_major_label(text):
    """去掉名称前的数字编号（如 01、0801）。"""
    if not text:
        return text
    return re.sub(r'^[\d.]+', '', str(text).strip()).strip() or str(text).strip()


def _major_group_id(row):
    """稳定门类 ID（内部用，与草稿字段对应）。"""
    label = (row.get('A') or '').strip()
    m = re.match(r'^(\d{2})', label)
    if m:
        return m.group(1)
    return f'r{row.get("_r")}'


def _eng_group_id(code_b):
    m = re.match(r'^(\d+)', (code_b or '').strip())
    return f'eng_{m.group(1)}' if m else f'eng_{(code_b or "").strip()}'


def _parse_major_names(text):
    """将专业说明文本拆分为可点选的专业名称列表。"""
    if not text:
        return []
    s = str(text).strip()
    s = re.sub(r'[（(][^）)]*未列举[^）)]*[）)]', '', s)
    s = re.sub(r'等等[。.…]*', '', s)
    s = re.sub(r'等[。.]?$', '', s)
    parts = re.split(r'[、，,；;]+', s)
    out = []
    seen = set()
    for p in parts:
        p = p.strip().strip('()（）').strip('…').strip('.').strip()
        if not p or len(p) < 2:
            continue
        if '未列举' in p or '请参考' in p or p in ('等', '等等'):
            continue
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _major_items_for_group(group_id, majors_text):
    return [
        {'id': f'{group_id}_m_{i + 1}', 'label': name}
        for i, name in enumerate(_parse_major_names(majors_text))
    ]


def _engineering_single_group(row, idx):
    code = (row.get('B') or '').strip()
    label = _strip_major_label(code)
    gid = _eng_group_id(code)
    majors_text = row.get('D') or row.get('C', '')
    return {
        'id': gid,
        'button_label': label,
        'title': label,
        'majors': majors_text,
        'major_items': _major_items_for_group(gid, majors_text),
        'note_field': f'eng_note_{idx}',
        'type': 'single',
    }


def _major_groups(rows):
    """专业意向：各学科门类 + 工学类下每个子类均为独立可选项（07 后插入）。"""
    groups = []
    eng_groups = []
    cat_note_i = 0
    eng_note_i = 0

    for row in rows:
        r = row.get('_r', 0)
        if 61 <= r <= 78 and row.get('A'):
            cat_note_i += 1
            label = _strip_major_label(row['A'])
            gid = _major_group_id(row)
            majors_text = row.get('C', '')
            groups.append({
                'id': gid,
                'button_label': label,
                'title': label,
                'majors': majors_text,
                'major_items': _major_items_for_group(gid, majors_text),
                'note_field': f'major_note_{cat_note_i}',
                'type': 'single',
            })
        elif (r == 79 and row.get('B')) or (r >= 80 and row.get('B')):
            eng_note_i += 1
            eng_groups.append(_engineering_single_group(row, eng_note_i))

    if eng_groups:
        insert_at = next((i for i, g in enumerate(groups) if g['id'] == '07'), len(groups) - 1)
        for offset, eng in enumerate(eng_groups):
            groups.insert(insert_at + 1 + offset, eng)

    return groups


_MUNICIPALITIES = frozenset({'北京市', '天津市', '上海市', '重庆市'})
_GAOKAO_PROVINCE_MUNI = frozenset({'北京', '天津', '上海', '重庆'})
_GAOKAO_PROVINCE_AUTONOMOUS = {
    '内蒙古': '内蒙古自治区',
    '广西': '广西壮族自治区',
    '西藏': '西藏自治区',
    '宁夏': '宁夏回族自治区',
    '新疆': '新疆维吾尔自治区',
}


def _gaokao_province_options():
    """一分一段 API 用简称 value，下拉展示完整省/市/自治区名称。"""
    options = []
    for code in PROVINCE_LIST:
        if code in _GAOKAO_PROVINCE_MUNI:
            label = code + '市'
        elif code in _GAOKAO_PROVINCE_AUTONOMOUS:
            label = _GAOKAO_PROVINCE_AUTONOMOUS[code]
        else:
            label = code + '省'
        options.append({'value': code, 'label': label})
    return options


def _region_rows():
    """省份选择 — 七行 + 每行喜欢的城市 / 非省会接受度"""
    raw = [
        ('华东地区', 'huadong', ['山东省', '江苏省', '安徽省', '浙江省', '福建省', '上海市']),
        ('华中地区', 'huazhong', ['湖北省', '湖南省', '河南省', '江西省']),
        ('华北地区', 'huabei', ['北京市', '天津市', '河北省', '山西省', '内蒙古自治区']),
        ('西南地区', 'xinan', ['四川省', '云南省', '贵州省', '西藏自治区', '重庆市']),
        ('东北地区', 'dongbei', ['辽宁省', '吉林省', '黑龙江省']),
        ('华南地区', 'huanan', ['广东省', '广西壮族自治区', '海南省']),
        ('西北地区', 'xibei', ['新疆维吾尔自治区', '宁夏回族自治区', '甘肃省', '陕西省', '青海省']),
    ]
    rows = []
    for title, row_slug, names in raw:
        provinces = []
        for name in names:
            slug = (
                name.replace('维吾尔自治区', '')
                .replace('回族自治区', '')
                .replace('自治区', '')
                .replace('省', '')
                .replace('市', '')
            )
            provinces.append({
                'name': name,
                'field': 'region_' + slug,
                'is_municipality': name in _MUNICIPALITIES,
            })
        rows.append({
            'title': title,
            'field_prefix': 'region_' + row_slug,
            'provinces': provinces,
        })
    return rows


@live_template_bp.route('/live-template')
def index():
    return render_template(
        'live_template/index.html',
        show_sidebar=True,
        active_nav='live_template',
        page_title='直播模板',
        page_subtitle='测评与讲解用表格',
    )


def _split_major_groups(groups):
    general = [g for g in groups if not g['id'].startswith('eng_')]
    engineering = [g for g in groups if g['id'].startswith('eng_')]
    return general, engineering


@live_template_bp.route('/live-template/api/college-major-scores')
def api_college_major_scores():
    q = (request.args.get('q') or '').strip()
    school = (request.args.get('school') or '').strip()
    major = (request.args.get('major') or '').strip()
    try:
        limit = int(request.args.get('limit', 80))
    except (TypeError, ValueError):
        limit = 80
    limit = max(1, min(limit, 200))
    dataset_id = (request.args.get('dataset') or 'jilin_2026').strip()
    return jsonify(search_records(dataset_id, q, school, major, limit))


@live_template_bp.route('/live-template/api/college-major-scores/schools')
def api_college_major_schools():
    q = (request.args.get('q') or '').strip()
    try:
        limit = int(request.args.get('limit', 40))
    except (TypeError, ValueError):
        limit = 40
    limit = max(1, min(limit, 100))
    dataset_id = (request.args.get('dataset') or 'jilin_2026').strip()
    return jsonify(list_schools(dataset_id, q, limit))


@live_template_bp.route('/live-template/api/elective-rating')
def api_elective_rating():
    birthday = (request.args.get('birthday') or '').strip()
    subjects = (request.args.get('subjects') or '').strip()
    result = lookup_elective_comprehensive(birthday, subjects)
    result['comp_ready'] = comprehensive_ready()
    return jsonify(result)


@live_template_bp.route('/live-template/api/enrollment-plan/search')
def api_enrollment_plan_search():
    school = (request.args.get('school') or '').strip()
    major = (request.args.get('major') or '').strip()
    province = (request.args.get('province') or '吉林').strip()
    try:
        limit = int(request.args.get('limit', 100))
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 200))
    dataset_id = 'jilin_2025' if province in ('吉林', '吉林省') else ''
    if not dataset_id:
        return jsonify({
            'ok': False,
            'message': '暂仅支持吉林省招生计划查询',
            'records': [],
            'total': 0,
        })
    return jsonify(enrollment_plan_search(
        'jilin_2025',
        school=school,
        major=major,
        limit=limit,
        batch=(request.args.get('batch') or '').strip(),
        category=(request.args.get('category') or '').strip(),
        reselect_subjects=(request.args.get('reselect') or '').strip(),
        enrollment_gender=(request.args.get('gender') or '').strip(),
    ))


def _build_enrollment_plan_filters():
    """模板用筛选项：{ key, label, options: [{value, label}] }。"""
    data = enrollment_plan_filter_options('jilin_2025')
    opts = data.get('filters') or {}
    labels = data.get('labels') or ENROLLMENT_PLAN_FILTER_LABELS
    out = []
    for key in ('batch', 'category', 'reselect_subjects', 'enrollment_gender'):
        options = []
        for val in opts.get(key) or ENROLLMENT_PLAN_FILTER_OPTIONS.get(key, ['']):
            options.append({'value': val, 'label': '全部' if not val else val})
        out.append({'key': key, 'label': labels.get(key, key), 'options': options})
    return out


@live_template_bp.route('/live-template/api/enrollment-plan/schools')
def api_enrollment_plan_schools():
    q = (request.args.get('q') or '').strip()
    province = (request.args.get('province') or '吉林').strip()
    try:
        limit = int(request.args.get('limit', 60))
    except (TypeError, ValueError):
        limit = 60
    limit = max(1, min(limit, 100))
    if province not in ('吉林', '吉林省'):
        return jsonify({'ok': False, 'schools': [], 'message': '暂仅支持吉林省'})
    return jsonify(enrollment_plan_schools('jilin_2025', q, limit))


@live_template_bp.route('/live-template/api/college-major-scores/lookup')
def api_college_major_lookup():
    school = (request.args.get('school') or '').strip()
    major = (request.args.get('major') or '').strip()
    subject_track = (request.args.get('subject_track') or '').strip()
    dataset_id = (request.args.get('dataset') or 'jilin_2026').strip()
    return jsonify(lookup_record(dataset_id, school, major, subject_track))


def build_gaokao_career_context(
    user_label='曹先生',
    default_name='童未来',
    active_nav='live_template',
    page_title=None,
    page_subtitle=None,
):
    rows = _load_gaokao_rows()
    score_ref = load_dataset('jilin_2026') or {}
    score_ref_status = dataset_status('jilin_2026')
    enroll_status = enrollment_plan_status('jilin_2025')
    return {
        'show_sidebar': True,
        'active_nav': active_nav,
        'page_title': page_title or '普通高考职业测评表',
        'page_subtitle': page_subtitle or f'使用人：{user_label}',
        'user_label': user_label,
        'default_name': default_name,
        'early_batch': _early_batch_policies(rows),
        'major_disciplines': load_major_disciplines(),
        'region_rows': _region_rows(),
        'gaokao_provinces': PROVINCE_LIST,
        'gaokao_province_options': _gaokao_province_options(),
        'score_rank_lookup_url': url_for('gaokao_apply.api_lookup'),
        'score_ref_title': score_ref.get('title') or score_ref_status.get('title') or '院校专业分数参考',
        'score_ref_columns': score_ref.get('columns') or [],
        'score_ref_count': score_ref_status.get('count') or 0,
        'score_ref_search_url': url_for('live_template.api_college_major_scores'),
        'score_ref_lookup_url': url_for('live_template.api_college_major_lookup'),
        'score_ref_schools_url': url_for('live_template.api_college_major_schools'),
        'elective_rating_url': url_for('live_template.api_elective_rating'),
        'enrollment_plan_title': enroll_status.get('title') or '吉林省2025招生计划查询',
        'enrollment_plan_columns': ENROLLMENT_PLAN_COLUMNS,
        'enrollment_plan_count': enroll_status.get('count') or 0,
        'enrollment_plan_year': enroll_status.get('year') or 2025,
        'enrollment_plan_search_url': url_for('live_template.api_enrollment_plan_search'),
        'enrollment_plan_schools_url': url_for('live_template.api_enrollment_plan_schools'),
        'enrollment_plan_filters': _build_enrollment_plan_filters(),
        'content_class': 'content-area--wide content-area--gaokao-full',
    }


@live_template_bp.route('/live-template/gaokao-career/cao')
def gaokao_career_cao():
    ctx = build_gaokao_career_context(
        user_label='曹先生',
        default_name='童未来',
        page_subtitle='使用人：曹先生',
    )
    return render_template('live_template/gaokao_career.html', **ctx)
