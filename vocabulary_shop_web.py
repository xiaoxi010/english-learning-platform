# vocabulary_shop_web.py - 商城词汇数据库

from flask import Blueprint, render_template, request, jsonify

from vocabulary_shop_manager import VocabularyManager

import sqlite3

# 独立 URL 前缀，避免与旧版 vocabulary_bp 的 /api/* 路由冲突
vocabulary_shop_bp = Blueprint('vocabulary_shop', __name__, url_prefix='/vocabulary_shop')

vocab_manager = VocabularyManager()



# ==================== 页面路由 ====================



@vocabulary_shop_bp.route('/')
def vocabulary_page():
    """词汇管理主页面"""
    return render_template('vocabulary_shop.html')





# ==================== API接口 ====================



@vocabulary_shop_bp.route('/api/dictionaries')

def get_dictionaries():

    """获取所有词典"""

    dictionaries = vocab_manager.get_dictionaries_ordered()

    dict_status = vocab_manager.get_dictionary_status()



    result = []

    for d in dictionaries:

        result.append({

            'id': d['id'],

            'name': d['dict_name'],

            'is_active': dict_status.get(d['dict_name'], True),

            'group_count': d['group_count'],

            'description': d.get('description', ''),

        })

    return jsonify(result)





@vocabulary_shop_bp.route('/api/dictionary/add', methods=['POST'])

def add_dictionary():

    """添加词典"""

    data = request.get_json()

    name = data.get('name', '').strip()

    desc = data.get('description', '').strip()



    if not name:

        return jsonify({'success': False, 'message': '词典名称不能为空'})



    if vocab_manager.add_dictionary(name, desc):

        return jsonify({'success': True, 'message': f'词典 "{name}" 添加成功'})

    return jsonify({'success': False, 'message': '添加失败，可能名称已存在'})





@vocabulary_shop_bp.route('/api/dictionary/delete', methods=['POST'])

def delete_dictionary():

    """删除词典"""

    data = request.get_json()

    name = data.get('name', '')



    if vocab_manager.delete_dictionary(name):

        return jsonify({'success': True, 'message': f'词典 "{name}" 已删除'})

    return jsonify({'success': False, 'message': '删除失败'})





@vocabulary_shop_bp.route('/api/dictionary/toggle', methods=['POST'])

def toggle_dictionary():

    """切换词典激活状态"""

    data = request.get_json()

    name = data.get('name', '')

    is_active = data.get('is_active', True)



    if vocab_manager.set_dictionary_status(name, is_active):

        return jsonify({'success': True})

    return jsonify({'success': False, 'message': '操作失败'})





@vocabulary_shop_bp.route('/api/dictionary/reorder', methods=['POST'])

def reorder_dictionaries():

    """更新词典顺序"""

    data = request.get_json()

    names = data.get('names', [])



    if vocab_manager.update_dictionary_order(names):

        return jsonify({'success': True})

    return jsonify({'success': False, 'message': '排序失败'})





@vocabulary_shop_bp.route('/api/groups')

def get_groups():

    """获取单词组列表"""

    sort_by = request.args.get('sort', 'name')

    groups = vocab_manager.get_all_groups_sorted(sort_by)

    return jsonify(groups)





@vocabulary_shop_bp.route('/api/group/<dict_name>/<group_name>')

def get_group_detail(dict_name, group_name):

    """获取单词组详情"""

    group = vocab_manager.get_word_group(group_name, dict_name)

    if group:

        if group.get('created_time'):

            group['created_time'] = str(group['created_time'])

        return jsonify(group)

    return jsonify({'error': '未找到该单词组'}), 404





@vocabulary_shop_bp.route('/api/group/add', methods=['POST'])

def add_group():

    """添加单词组"""

    data = request.get_json()

    group_name = data.get('group_name', '').strip()

    dict_name = data.get('dict_name', '').strip()

    words_text = data.get('words_text', '')



    if not dict_name:

        return jsonify({'success': False, 'message': '请先选择或创建一个词典'})

    if not group_name:

        return jsonify({'success': False, 'message': '请输入组名'})



    words_data = []

    for line in words_text.strip().split('\n'):

        line = line.strip()

        if line:

            parts = line.split(' ', 2)

            if len(parts) >= 3:

                words_data.append({

                    'word': parts[0],

                    'part_of_speech': parts[1],

                    'chinese_meaning': parts[2]

                })



    if not words_data:

        return jsonify({'success': False, 'message': '请输入有效的单词数据（每行格式：单词 词性 中文意思）'})



    if vocab_manager.add_word_group(group_name, words_data, '', dict_name):

        return jsonify({'success': True, 'message': f'成功添加 {len(words_data)} 个单词到 "{group_name}"'})

    return jsonify({'success': False, 'message': '添加失败'})





@vocabulary_shop_bp.route('/api/group/delete', methods=['POST'])

def delete_group():

    """删除单词组"""

    data = request.get_json()

    group_name = data.get('group_name', '')

    dict_name = data.get('dict_name', '').strip()



    if not dict_name:

        return jsonify({'success': False, 'message': '词典名称无效'})



    if vocab_manager.delete_word_group(group_name, dict_name):

        return jsonify({'success': True, 'message': '删除成功'})

    return jsonify({'success': False, 'message': '删除失败'})





@vocabulary_shop_bp.route('/api/search')

def search_words():

    """搜索单词"""

    keyword = request.args.get('keyword', '').strip()

    search_by = request.args.get('by', 'all')

    deduplicate = request.args.get('dedup', 'true').lower() == 'true'



    if not keyword:

        return jsonify({'results': [], 'count': 0})



    results = vocab_manager.search_words(keyword, search_by)



    if deduplicate:

        seen = set()

        unique_results = []

        for r in results:

            word_lower = r['word'].lower()

            if word_lower not in seen:

                seen.add(word_lower)

                unique_results.append(r)

        results = unique_results



    return jsonify({

        'results': results,

        'count': len(results),

        'keyword': keyword

    })





@vocabulary_shop_bp.route('/api/statistics')

def get_statistics():

    """获取统计信息"""

    stats = vocab_manager.get_statistics()

    for ds in stats.get('dictionary_statistics', []):

        if ds.get('created_time'):

            ds['created_time'] = str(ds['created_time'])

    return jsonify(stats)





@vocabulary_shop_bp.route('/api/export/excel')

def export_to_excel():

    """导出所有数据到Excel"""

    import tempfile

    import os



    try:

        temp_dir = tempfile.gettempdir()

        file_path = os.path.join(temp_dir, '词汇数据库.xlsx')



        if vocab_manager.export_to_excel(file_path):

            from flask import send_file

            return send_file(

                file_path,

                as_attachment=True,

                download_name='词汇数据库.xlsx',

                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

            )

        return jsonify({'success': False, 'message': '导出失败'})

    except Exception as e:

        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'})





@vocabulary_shop_bp.route('/api/import/excel', methods=['POST'])

def import_from_excel():

    """从Excel导入数据"""

    import os

    import tempfile



    try:

        if 'file' not in request.files:

            return jsonify({'success': False, 'message': '请选择文件'})



        file = request.files['file']

        if file.filename == '':

            return jsonify({'success': False, 'message': '请选择文件'})



        temp_dir = tempfile.gettempdir()

        file_path = os.path.join(temp_dir, file.filename)

        file.save(file_path)



        dict_name = request.form.get('dict_name', None)



        if vocab_manager.import_from_excel(file_path, dict_name):

            os.remove(file_path)

            return jsonify({'success': True, 'message': 'Excel导入成功！'})

        return jsonify({'success': False, 'message': '导入失败，请检查文件格式'})



    except Exception as e:

        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'})





@vocabulary_shop_bp.route('/api/dictionary/rename', methods=['POST'])

def rename_dictionary():

    """修改词典名称"""

    data = request.get_json()

    old_name = data.get('old_name', '')

    new_name = data.get('new_name', '').strip()



    if not new_name:

        return jsonify({'success': False, 'message': '新名称不能为空'})



    try:

        conn = sqlite3.connect(vocab_manager.db_path)

        cursor = conn.cursor()

        cursor.execute('UPDATE dictionaries SET dict_name = ? WHERE dict_name = ?', (new_name, old_name))

        conn.commit()

        conn.close()

        return jsonify({'success': True, 'message': f'词典已从 "{old_name}" 改为 "{new_name}"'})

    except Exception as e:

        return jsonify({'success': False, 'message': f'修改失败: {str(e)}'})

