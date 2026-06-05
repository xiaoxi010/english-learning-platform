# gaokao_apply_web.py — 高考报考
from flask import Blueprint, jsonify, render_template, request, url_for

from gaokao_jilin_data_loader import (
    EXPERT_FIELDS,
    STRONG_BASE_FIELDS,
    SYSTEM_TITLE,
    dataset_status,
    filter_options,
    is_strong_base_dataset,
    list_province_batches,
    lookup_plan_prefer_batch,
    lookup_plan_prefer_meta,
    list_schools,
    resolve_dataset_id,
    search_records,
    system_status,
)
from gaokao_province_registry import list_apply_provinces_status, norm_province
from live_template_web import _gaokao_province_options, _region_rows
from major_catalog import load_major_disciplines
from score_rank_loader import (
    PROVINCE_LIST,
    list_provinces_status,
    load_score_rank,
    lookup,
    province_data_available,
    province_subject_labels,
)

gaokao_apply_bp = Blueprint('gaokao_apply', __name__)

GENDER_OPTIONS = ['男', '女']
ETHNICITY_OPTIONS = [
    '汉族', '满族', '朝鲜族', '蒙古族', '回族', '藏族', '维吾尔族', '苗族', '彝族', '壮族',
    '布依族', '侗族', '瑶族', '白族', '土家族', '哈尼族', '哈萨克族', '傣族', '黎族', '其他',
]


def _apply_region_rows():
    rows = _region_rows()
    for row in rows:
        for prov in row['provinces']:
            name = prov['name']
            prov['code'] = (
                name.replace('维吾尔自治区', '')
                .replace('回族自治区', '')
                .replace('自治区', '')
                .replace('省', '')
                .replace('市', '')
            )
    return rows


def _default_gaokao_province_label(region_code):
    for opt in _gaokao_province_options():
        if opt['value'] == region_code:
            return opt['label']
    return region_code


def _apply_gaokao_province_options():
    """高考省份下拉：仅含已导入志愿数据的省份（当前约 29 省）。"""
    available = {
        row['province']
        for row in list_apply_provinces_status()
        if row.get('available')
    }
    return [opt for opt in _gaokao_province_options() if opt['value'] in available]


def _default_apply_province():
    for row in list_apply_provinces_status():
        if row.get('available'):
            return row['province']
    return '吉林'


@gaokao_apply_bp.route('/gaokao-apply')
def index():
    default_region = _default_apply_province()
    apply_options = _apply_gaokao_province_options()
    return render_template(
        'gaokao_apply/apply_profile.html',
        show_sidebar=True,
        active_nav='gaokao_apply',
        page_title='高考报考',
        top_back_url=url_for('index'),
        top_back_label='← 返回主界面',
        content_class='content-area--wide content-area--gaokao-full',
        province_list=PROVINCE_LIST,
        default_region=default_region,
        default_gaokao_province_label=_default_gaokao_province_label(default_region),
        gaokao_province_options=apply_options or _gaokao_province_options(),
        gender_options=GENDER_OPTIONS,
        ethnicity_options=ETHNICITY_OPTIONS,
        major_disciplines=load_major_disciplines(),
        region_rows=_apply_region_rows(),
        lookup_url=url_for('gaokao_apply.api_lookup'),
        system_url=url_for('gaokao_apply.apply_system_page'),
    )


@gaokao_apply_bp.route('/gaokao-apply/system')
def apply_system_page():
    province = _request_province()
    status = system_status(province)
    batch_info = list_province_batches(province)
    expert = dataset_status(resolve_dataset_id('undergraduate', province))
    subtitle = f'{province}省普通高考与强基计划数据查询' if province != '上海' else f'{province}市普通高考与强基计划数据查询'
    if province in ('北京', '天津', '重庆'):
        subtitle = f'{province}市普通高考与强基计划数据查询'
    return render_template(
        'gaokao_apply/jilin_data.html',
        show_sidebar=True,
        active_nav='gaokao_apply',
        page_title=SYSTEM_TITLE,
        page_subtitle=subtitle,
        gaokao_province=province,
        province_batches=batch_info['batches'],
        default_batch=batch_info['default_batch'],
        batch_labels=batch_info['batch_labels'],
        record_count=status.get('total_count') or 0,
        expert_count=expert.get('count') or 0,
        strong_count=status.get('strong_base_count') or 0,
        expert_columns=[{'key': k, 'label': lb} for k, lb in EXPERT_FIELDS],
        strong_columns=[{'key': k, 'label': lb} for k, lb in STRONG_BASE_FIELDS],
        search_url=url_for('gaokao_apply.api_jilin_data_search'),
        schools_url=url_for('gaokao_apply.api_jilin_data_schools'),
        filters_url=url_for('gaokao_apply.api_jilin_data_filters'),
        plan_url=url_for('gaokao_apply.apply_plan_page', province=province),
        content_class='content-area--wide content-area--gaokao-full content-area--jilin-system',
        jilin_system_toolbar=True,
        jilin_back_url=url_for('gaokao_apply.index'),
    )


@gaokao_apply_bp.route('/gaokao-apply/api/jilin-data/plan-lookup', methods=['POST'])
def api_jilin_plan_lookup():
    body = request.get_json(silent=True) or {}
    ds = _dataset_key((body.get('dataset') or 'undergraduate').strip())
    batch = (body.get('batch') or body.get('batch_name') or '').strip()
    items = body.get('items') or []
    if not isinstance(items, list):
        items = []
    items = items[:300]
    return jsonify({
        'ok': True,
        'dataset': ds,
        'results': lookup_plan_prefer_batch(ds, items, batch_name=batch),
    })


@gaokao_apply_bp.route('/gaokao-apply/plan')
def apply_plan_page():
    province = _request_province()
    batch_info = list_province_batches(province)
    return render_template(
        'gaokao_apply/plan.html',
        show_sidebar=True,
        active_nav='gaokao_apply',
        page_title='志愿表',
        page_subtitle='根据各批次优选结果生成；可拖动排序、折叠院校，支持打印',
        gaokao_province=province,
        province_batches=batch_info['batches'],
        default_batch=batch_info['default_batch'],
        batch_labels=batch_info['batch_labels'],
        system_url=url_for('gaokao_apply.apply_system_page', province=province),
        profile_url=url_for('gaokao_apply.index'),
        plan_lookup_url=url_for('gaokao_apply.api_jilin_plan_lookup'),
        content_class='content-area--wide content-area--gaokao-full content-area--jilin-plan',
    )


@gaokao_apply_bp.route('/gaokao-apply/jilin-expert')
@gaokao_apply_bp.route('/gaokao-apply/jilin-strong-base')
def jilin_legacy_redirect():
    from flask import redirect
    return redirect(url_for('gaokao_apply.apply_system_page'))


def _request_province():
    body = request.get_json(silent=True) or {}
    raw = (
        request.args.get('province')
        or body.get('province')
        or body.get('gaokao_province')
        or ''
    ).strip()
    return norm_province(raw) or '吉林'


def _dataset_key(name):
    return resolve_dataset_id(name, _request_province())


@gaokao_apply_bp.route('/gaokao-apply/api/jilin-data/search')
def api_jilin_data_search():
    ds = _dataset_key((request.args.get('dataset') or 'undergraduate').strip())
    try:
        limit = int(request.args.get('limit', 100))
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 500))
    user_rank = None
    user_score = None
    rank_raw = (request.args.get('user_rank') or '').strip()
    score_raw = (request.args.get('user_score') or '').strip()
    if rank_raw:
        try:
            user_rank = int(rank_raw)
        except (TypeError, ValueError):
            user_rank = None
    if score_raw:
        try:
            user_score = int(score_raw)
        except (TypeError, ValueError):
            user_score = None
    sort_by_score = (request.args.get('sort_by_score') or '').strip() in ('1', 'true', 'yes')
    view = (request.args.get('view') or '').strip()
    extra_schools = (request.args.get('extra_schools') or '').strip()
    return jsonify(search_records(
        ds,
        school=(request.args.get('school') or '').strip(),
        major=(request.args.get('major') or '').strip(),
        batch=(request.args.get('batch') or '').strip(),
        category=(request.args.get('category') or '').strip(),
        school_type=(request.args.get('type') or '').strip(),
        provinces=(request.args.get('provinces') or '').strip(),
        major_categories=(request.args.get('major_categories') or '').strip(),
        major_groups=(request.args.get('major_groups') or '').strip(),
        user_rank=user_rank,
        user_score=user_score,
        limit=limit,
        sort_by_score=sort_by_score,
        view=view,
        extra_schools=extra_schools,
    ))


@gaokao_apply_bp.route('/gaokao-apply/api/jilin-data/schools')
def api_jilin_data_schools():
    ds = _dataset_key((request.args.get('dataset') or 'undergraduate').strip())
    q = (request.args.get('q') or '').strip()
    provinces = (request.args.get('provinces') or '').strip()
    batch = (request.args.get('batch') or '').strip()
    try:
        limit = int(request.args.get('limit', 60))
    except (TypeError, ValueError):
        limit = 60
    if batch and not is_strong_base_dataset(ds):
        result = search_records(
            ds,
            school=q,
            batch=batch,
            provinces=provinces,
            limit=max(1, min(limit, 100)),
            view='school',
        )
        if not result.get('ok'):
            return jsonify({'ok': False, 'schools': [], 'message': result.get('message') or ''})
        schools = []
        for card in result.get('records') or []:
            name = str(card.get('school_name') or '').strip()
            if not name:
                continue
            schools.append({
                'school_name': name,
                'province': card.get('province') or '',
                'school_code': card.get('school_code') or '',
                'in_selected_region': card.get('in_selected_region', False),
            })
        return jsonify({'ok': True, 'schools': schools})
    return jsonify(list_schools(ds, q, max(1, min(limit, 100)), provinces))


@gaokao_apply_bp.route('/gaokao-apply/api/jilin-data/filters')
def api_jilin_data_filters():
    ds = _dataset_key((request.args.get('dataset') or 'undergraduate').strip())
    batch = (request.args.get('batch') or '').strip()
    return jsonify(filter_options(ds, batch=batch))


@gaokao_apply_bp.route('/gaokao-apply/score-rank')
def score_rank_page():
    provinces = list_provinces_status()
    default = '吉林' if province_data_available('吉林') else next(
        (p['name'] for p in provinces if p['available']),
        PROVINCE_LIST[0],
    )
    return render_template(
        'gaokao_apply/score_rank.html',
        show_sidebar=True,
        active_nav='gaokao_apply',
        page_title='分数与位次',
        page_subtitle='2025年高考一分一段查询',
        provinces=provinces,
        default_province=default,
        data_dir_hint='data/score_rank/',
    )


@gaokao_apply_bp.route('/gaokao-apply/api/provinces')
def api_provinces():
    return jsonify({'provinces': list_provinces_status()})


@gaokao_apply_bp.route('/gaokao-apply/api/lookup', methods=['POST'])
def api_lookup():
    body = request.get_json(silent=True) or {}
    province = (body.get('province') or request.form.get('province') or '').strip()
    subject = (body.get('subject') or request.form.get('subject') or 'physics').strip()
    score_raw = body.get('score') if body is not None else request.form.get('score')
    if province not in PROVINCE_LIST:
        return jsonify({'ok': False, 'error': 'invalid_province', 'message': '省份无效'}), 400
    if subject not in ('physics', 'history'):
        subject = 'physics'
    try:
        score = int(score_raw)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'invalid_score', 'message': '请输入有效分数'}), 400
    if score < 0 or score > 900:
        return jsonify({'ok': False, 'error': 'invalid_score', 'message': '分数超出合理范围'}), 400
    result = lookup(province, subject, score)
    labels = province_subject_labels(province)
    result['province'] = province
    result['subject'] = subject
    result['score'] = score
    result['subject_labels'] = labels
    status = 200 if result.get('ok') else 404
    if result.get('error') == 'data_missing':
        status = 503
    return jsonify(result), status


@gaokao_apply_bp.route('/gaokao-apply/api/apply-provinces')
def api_apply_provinces():
    return jsonify({'provinces': list_apply_provinces_status()})


@gaokao_apply_bp.route('/gaokao-apply/api/province-batches')
def api_province_batches():
    province = _request_province()
    return jsonify(list_province_batches(province))


@gaokao_apply_bp.route('/gaokao-apply/api/status')
def api_status():
    return jsonify({
        'total': len(PROVINCE_LIST),
        'available': [p['name'] for p in list_provinces_status() if p['available']],
    })
