# exam_web.py - 考试记录管理网页版
from flask import Blueprint, render_template, request, jsonify, send_file, session, redirect, url_for
from exam_stats_db import get_exam_stats_db
from exam_png_exporter import ExamPNGExporter
from settings_web import login_required
import os
import tempfile

exam_bp = Blueprint('exam', __name__)
png_exporter = ExamPNGExporter()


@exam_bp.before_request
def require_login():
    if 'user' not in session:
        session['next_url'] = request.url
        return redirect(url_for('login'))


# ==================== 页面 ====================

@exam_bp.route('/exam_database')
def exam_database_page():
    """考试数据库页面"""
    dictionaries = get_exam_stats_db().get_dictionaries_list()
    return render_template('exam_database.html', dictionaries=dictionaries, active_nav='exam_db')


# ==================== API ====================

@exam_bp.route('/api/exam/stats')
def api_stats():
    """获取单词组统计"""
    stats_db = get_exam_stats_db()
    dict_name = request.args.get('dict', '全部')
    sort_by = request.args.get('sort', 'group_name')
    
    if dict_name == '全部':
        dict_name = None
    
    stats = stats_db.get_all_stats_with_vocab(dict_name)
    
    # 排序
    if sort_by == 'group_name':
        stats.sort(key=lambda x: str(x['group_name']))
    elif sort_by == 'challenge_count':
        stats.sort(key=lambda x: int(x['challenge_count']) if x['challenge_count'] != '-' else -1, reverse=True)
    elif sort_by == 'pass_count':
        stats.sort(key=lambda x: int(x['pass_count']) if x['pass_count'] != '-' else -1, reverse=True)
    elif sort_by == 'highest_score':
        stats.sort(key=lambda x: float(x['highest_score']) if x['highest_score'] != '-' else -1, reverse=True)
    elif sort_by == 'gpa':
        stats.sort(key=lambda x: float(x['gpa']) if x['gpa'] != '-' else -1, reverse=True)
    elif sort_by == 'earliest_pass_time':
        stats.sort(key=lambda x: x['earliest_pass_time'] if x['earliest_pass_time'] != '-' else '', reverse=True)
    
    return jsonify(stats)


@exam_bp.route('/api/exam/records')
def api_records():
    """获取详细考核记录"""
    stats_db = get_exam_stats_db()
    dict_name = request.args.get('dict', '全部')
    limit = int(request.args.get('limit', 500))
    
    if dict_name == '全部':
        dict_name = None
    
    records = stats_db.get_all_exam_records(dict_name, limit)
    
    # 转换布尔值
    for r in records:
        r['is_passed'] = bool(r['is_passed'])
    
    return jsonify(records)


@exam_bp.route('/api/exam/record/<int:record_id>')
def api_record_detail(record_id):
    """获取单条记录详情"""
    record = get_exam_stats_db().get_exam_record_by_id(record_id)
    if not record:
        return jsonify({'error': '未找到记录'}), 404
    record['is_passed'] = bool(record['is_passed'])
    return jsonify(record)


@exam_bp.route('/api/exam/record/<int:record_id>/update', methods=['POST'])
def api_record_update(record_id):
    """更新考核记录"""
    data = request.get_json() or {}
    updated = get_exam_stats_db().update_exam_record(record_id, data)
    if not updated:
        return jsonify({'success': False, 'message': '更新失败或记录不存在'}), 404
    updated['is_passed'] = bool(updated['is_passed'])
    return jsonify({'success': True, 'record': updated})


@exam_bp.route('/api/exam/summary')
def api_summary():
    """获取统计摘要"""
    summary = get_exam_stats_db().get_statistics_summary()
    return jsonify(summary)


@exam_bp.route('/api/exam/export_png/<int:record_id>')
def api_export_png(record_id):
    """导出PNG"""
    records = get_exam_stats_db().get_all_exam_records(limit=1000)
    record = None
    for r in records:
        if r['id'] == record_id:
            record = r
            break
    
    if not record:
        return jsonify({'error': '未找到记录'}), 404
    
    try:
        temp_dir = tempfile.gettempdir()
        filename = f"{record['pattern_name']}_{record['group_name']}_{record['exam_time'][:10]}.png"
        file_path = os.path.join(temp_dir, filename)
        
        png_exporter.export(record, file_path)
        
        return send_file(file_path, as_attachment=True, download_name=filename, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500


@exam_bp.route('/api/exam/clear', methods=['POST'])
def api_clear():
    """清空所有记录"""
    if get_exam_stats_db().clear_all_records():
        return jsonify({'success': True, 'message': '已清空所有记录'})
    return jsonify({'success': False, 'message': '清空失败'})


@exam_bp.route('/api/exam/dictionaries')
def api_dictionaries():
    """获取词典列表"""
    return jsonify(get_exam_stats_db().get_dictionaries_list())
