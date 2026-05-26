# skill_db_web.py
from flask import Blueprint, render_template, request, jsonify, session, send_file
import sqlite3
import json
import os
import pandas as pd
from datetime import datetime
import hashlib
from werkzeug.utils import secure_filename
import uuid

skill_db_bp = Blueprint('skill_db', __name__)

# 配置
DATABASE = 'skill_database.db'
UPLOAD_FOLDER = 'skill_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

# 确保上传文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('skill_exports', exist_ok=True)


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_skill_database():
    """初始化技能数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resource_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER,
            uploader TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            file_path TEXT,
            tags TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES question_categories (id),
            UNIQUE(category_id, name)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS single_choice_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            question TEXT NOT NULL,
            question_image TEXT,
            correct_answer TEXT NOT NULL,
            wrong_answer1 TEXT,
            wrong_answer2 TEXT,
            wrong_answer3 TEXT,
            explanation TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS multi_choice_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            question TEXT NOT NULL,
            question_image TEXT,
            correct_answers TEXT,
            answer_options TEXT,
            explanation TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fill_in_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            question TEXT NOT NULL,
            question_image TEXT,
            answer TEXT NOT NULL,
            explanation TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_answer_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            question TEXT NOT NULL,
            question_image TEXT,
            answer TEXT NOT NULL,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            scenario TEXT NOT NULL,
            sub_questions TEXT,
            sub_answers TEXT,
            sub_explanations TEXT,
            explanation TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("技能数据库初始化完成")


# 初始化数据库
init_skill_database()


@skill_db_bp.route('/')
def skill_db_page():
    """技能数据库主页面"""
    return render_template('skill_db.html', user_name=session.get('user_name', '未登录'))


# ==================== 分类管理API ====================

@skill_db_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有分类"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.*, 
               (SELECT COUNT(*) FROM question_groups WHERE category_id = c.id) as group_count
        FROM question_categories c
        ORDER BY c.created_time DESC
    ''')
    
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'data': categories})


@skill_db_bp.route('/api/categories', methods=['POST'])
def add_category():
    """添加分类"""
    data = request.json
    name = data.get('name', '').strip()
    description = data.get('description', '')
    
    if not name:
        return jsonify({'success': False, 'message': '分类名称不能为空'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO question_categories (name, description) VALUES (?, ?)',
            (name, description)
        )
        conn.commit()
        return jsonify({'success': True, 'message': '分类添加成功'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '分类名称已存在'})
    finally:
        conn.close()


@skill_db_bp.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """更新分类"""
    data = request.json
    name = data.get('name', '').strip()
    description = data.get('description', '')
    
    if not name:
        return jsonify({'success': False, 'message': '分类名称不能为空'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'UPDATE question_categories SET name = ?, description = ? WHERE id = ?',
            (name, description, category_id)
        )
        conn.commit()
        return jsonify({'success': True, 'message': '分类更新成功'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '分类名称已存在'})
    finally:
        conn.close()


@skill_db_bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """删除分类"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM question_groups WHERE category_id = ?', (category_id,))
        cursor.execute('DELETE FROM question_categories WHERE id = ?', (category_id,))
        conn.commit()
        return jsonify({'success': True, 'message': '分类删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()


# ==================== 分组管理API ====================

@skill_db_bp.route('/api/groups/<int:category_id>', methods=['GET'])
def get_groups(category_id):
    """获取指定分类下的所有分组"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT g.*, 
               (SELECT COUNT(*) FROM single_choice_questions WHERE group_id = g.id) +
               (SELECT COUNT(*) FROM multi_choice_questions WHERE group_id = g.id) +
               (SELECT COUNT(*) FROM fill_in_questions WHERE group_id = g.id) +
               (SELECT COUNT(*) FROM short_answer_questions WHERE group_id = g.id) +
               (SELECT COUNT(*) FROM application_questions WHERE group_id = g.id) as total_questions
        FROM question_groups g
        WHERE g.category_id = ?
        ORDER BY g.created_time DESC
    ''', (category_id,))
    
    groups = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'data': groups})


@skill_db_bp.route('/api/groups', methods=['POST'])
def add_group():
    """添加分组"""
    data = request.json
    category_id = data.get('category_id')
    name = data.get('name', '').strip()
    description = data.get('description', '')
    
    if not category_id:
        return jsonify({'success': False, 'message': '请选择分类'})
    if not name:
        return jsonify({'success': False, 'message': '分组名称不能为空'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO question_groups (category_id, name, description) VALUES (?, ?, ?)',
            (category_id, name, description)
        )
        conn.commit()
        return jsonify({'success': True, 'message': '分组添加成功'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '该分类下分组名称已存在'})
    finally:
        conn.close()

@skill_db_bp.route('/api/questions/reorder_ids', methods=['POST'])
def reorder_question_ids():
    """一键重新分配ID - 按分组重新编号"""
    data = request.json
    group_id = data.get('group_id')
    
    if not group_id:
        return jsonify({'success': False, 'message': '请选择分组'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        tables = {
            'single_choice_questions': ['group_id', 'question', 'correct_answer', 'wrong_answer1', 'wrong_answer2', 'wrong_answer3', 'explanation', 'question_image', 'created_time'],
            'multi_choice_questions': ['group_id', 'question', 'correct_answers', 'answer_options', 'explanation', 'question_image', 'created_time'],
            'fill_in_questions': ['group_id', 'question', 'answer', 'explanation', 'question_image', 'created_time'],
            'short_answer_questions': ['group_id', 'question', 'answer', 'question_image', 'created_time'],
            'application_questions': ['group_id', 'scenario', 'sub_questions', 'sub_answers', 'sub_explanations', 'explanation', 'created_time']
        }
        
        for table, columns in tables.items():
            cols = ', '.join(columns)
            placeholders = ', '.join(['?'] * len(columns))
            
            # 读取所有数据
            cursor.execute(f'SELECT {cols} FROM {table} WHERE group_id = ? ORDER BY id', (group_id,))
            rows = cursor.fetchall()
            
            if not rows:
                continue
            
            # 删除原数据
            cursor.execute(f'DELETE FROM {table} WHERE group_id = ?', (group_id,))
            
            # 重新插入
            for row in rows:
                cursor.execute(f'INSERT INTO {table} ({cols}) VALUES ({placeholders})', tuple(row))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'ID重新分配成功！'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'重新分配失败: {str(e)}'})
    
@skill_db_bp.route('/api/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    """更新分组"""
    data = request.json
    name = data.get('name', '').strip()
    description = data.get('description', '')
    
    if not name:
        return jsonify({'success': False, 'message': '分组名称不能为空'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        'UPDATE question_groups SET name = ?, description = ? WHERE id = ?',
        (name, description, group_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '分组更新成功'})


@skill_db_bp.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """删除分组"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM single_choice_questions WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM multi_choice_questions WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM fill_in_questions WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM short_answer_questions WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM application_questions WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM question_groups WHERE id = ?', (group_id,))
        conn.commit()
        return jsonify({'success': True, 'message': '分组删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()


# ==================== 题目管理API ====================

@skill_db_bp.route('/api/questions/<int:group_id>', methods=['GET'])
def get_questions(group_id):
    """获取分组下的题目"""
    question_type = request.args.get('type', 'single_choice')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if question_type == 'single_choice':
        cursor.execute('''
            SELECT id, question, correct_answer, explanation, created_time,
                   CASE WHEN question_image IS NOT NULL THEN 1 ELSE 0 END as has_image
            FROM single_choice_questions
            WHERE group_id = ?
            ORDER BY created_time DESC
        ''', (group_id,))
    elif question_type == 'multi_choice':
        cursor.execute('''
            SELECT id, question, correct_answers, explanation, created_time,
                   CASE WHEN question_image IS NOT NULL THEN 1 ELSE 0 END as has_image
            FROM multi_choice_questions
            WHERE group_id = ?
            ORDER BY created_time DESC
        ''', (group_id,))
    elif question_type == 'fill_in':
        cursor.execute('''
            SELECT id, question, answer, explanation, created_time,
                   CASE WHEN question_image IS NOT NULL THEN 1 ELSE 0 END as has_image
            FROM fill_in_questions
            WHERE group_id = ?
            ORDER BY created_time DESC
        ''', (group_id,))
    elif question_type == 'short_answer':
        cursor.execute('''
            SELECT id, question, answer, created_time,
                   CASE WHEN question_image IS NOT NULL THEN 1 ELSE 0 END as has_image
            FROM short_answer_questions
            WHERE group_id = ?
            ORDER BY created_time DESC
        ''', (group_id,))
    elif question_type == 'application':
        cursor.execute('''
            SELECT id, scenario, sub_questions, explanation, created_time
            FROM application_questions
            WHERE group_id = ?
            ORDER BY created_time DESC
        ''', (group_id,))
    else:
        conn.close()
        return jsonify({'success': True, 'data': []})
    
    questions = [dict(row) for row in cursor.fetchall()]
    
    if question_type == 'multi_choice':
        for q in questions:
            if q.get('correct_answers'):
                try:
                    q['correct_answers'] = json.loads(q['correct_answers'])
                except:
                    pass
    
    if question_type == 'application':
        for q in questions:
            if q.get('sub_questions'):
                try:
                    q['sub_questions'] = json.loads(q['sub_questions'])
                except:
                    pass
    
    conn.close()
    return jsonify({'success': True, 'data': questions})


@skill_db_bp.route('/api/questions/detail/<int:question_id>', methods=['GET'])
def get_question_detail(question_id):
    """获取单个题目详情"""
    question_type = request.args.get('type', 'single_choice')
    
    table_map = {
        'single_choice': 'single_choice_questions',
        'multi_choice': 'multi_choice_questions',
        'fill_in': 'fill_in_questions',
        'short_answer': 'short_answer_questions',
        'application': 'application_questions'
    }
    
    table_name = table_map.get(question_type)
    if not table_name:
        return jsonify({'success': False, 'message': '无效的题型'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(f'SELECT * FROM {table_name} WHERE id = ?', (question_id,))
    question = cursor.fetchone()
    conn.close()
    
    if not question:
        return jsonify({'success': False, 'message': '题目不存在'})
    
    question_dict = dict(question)
    
    # 处理JSON字段
    if question_type == 'multi_choice':
        for field in ['correct_answers', 'answer_options']:
            if question_dict.get(field):
                try:
                    parsed = json.loads(question_dict[field])
                    question_dict[field] = parsed
                except:
                    question_dict[field] = []
            else:
                question_dict[field] = []
    
    if question_type == 'application':
        for field in ['sub_questions', 'sub_answers', 'sub_explanations']:
            if question_dict.get(field):
                try:
                    question_dict[field] = json.loads(question_dict[field])
                except:
                    question_dict[field] = []
            else:
                question_dict[field] = []
    
    return jsonify({'success': True, 'data': question_dict})


@skill_db_bp.route('/api/questions/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """更新题目"""
    question_type = request.args.get('type', 'single_choice')
    data = request.json
    
    table_map = {
        'single_choice': 'single_choice_questions',
        'multi_choice': 'multi_choice_questions',
        'fill_in': 'fill_in_questions',
        'short_answer': 'short_answer_questions',
        'application': 'application_questions'
    }
    
    table_name = table_map.get(question_type)
    if not table_name:
        return jsonify({'success': False, 'message': '无效的题型'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if question_type == 'single_choice':
            cursor.execute(f'''
                UPDATE {table_name} 
                SET question = ?, correct_answer = ?, wrong_answer1 = ?, wrong_answer2 = ?, wrong_answer3 = ?, explanation = ?
                WHERE id = ?
            ''', (
                data.get('question', ''),
                data.get('correct_answer', ''),
                data.get('wrong_answer1', ''),
                data.get('wrong_answer2', ''),
                data.get('wrong_answer3', ''),
                data.get('explanation', ''),
                question_id
            ))
        elif question_type == 'multi_choice':
            # 获取前端传来的数据
            correct_answers = data.get('correct_answers', [])
            answer_options = data.get('options', data.get('answer_options', []))
            
            # 确保是列表
            if isinstance(correct_answers, str):
                correct_answers = [x.strip() for x in correct_answers.split(',') if x.strip()]
            if isinstance(answer_options, str):
                answer_options = [x.strip() for x in answer_options.split(',') if x.strip()]
            
            cursor.execute(f'''
                UPDATE {table_name} 
                SET question = ?, correct_answers = ?, answer_options = ?, explanation = ?
                WHERE id = ?
            ''', (
                data.get('question', ''),
                json.dumps(correct_answers, ensure_ascii=False),
                json.dumps(answer_options, ensure_ascii=False),
                data.get('explanation', ''),
                question_id
            ))
        elif question_type == 'fill_in':
            cursor.execute(f'''
                UPDATE {table_name} 
                SET question = ?, answer = ?, explanation = ?
                WHERE id = ?
            ''', (
                data.get('question', ''),
                data.get('answer', ''),
                data.get('explanation', ''),
                question_id
            ))
        elif question_type == 'short_answer':
            cursor.execute(f'''
                UPDATE {table_name} 
                SET question = ?, answer = ?
                WHERE id = ?
            ''', (
                data.get('question', ''),
                data.get('answer', ''),
                question_id
            ))
        elif question_type == 'application':
            sub_questions = data.get('sub_questions', [])
            sub_answers = data.get('sub_answers', [])
            sub_explanations = data.get('sub_explanations', [])
            
            cursor.execute(f'''
                UPDATE {table_name} 
                SET scenario = ?, sub_questions = ?, sub_answers = ?, sub_explanations = ?, explanation = ?
                WHERE id = ?
            ''', (
                data.get('scenario', ''),
                json.dumps(sub_questions, ensure_ascii=False),
                json.dumps(sub_answers, ensure_ascii=False),
                json.dumps(sub_explanations, ensure_ascii=False),
                data.get('explanation', ''),
                question_id
            ))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '题目更新成功'})
    except Exception as e:
        conn.close()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})


@skill_db_bp.route('/api/questions/single_choice', methods=['POST'])
def add_single_choice():
    """添加单选题"""
    data = request.json
    group_id = data.get('group_id')
    
    if not group_id:
        return jsonify({'success': False, 'message': '请选择分组'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO single_choice_questions 
        (group_id, question, correct_answer, wrong_answer1, wrong_answer2, wrong_answer3, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        group_id,
        data.get('question', ''),
        data.get('correct_answer', ''),
        data.get('wrong_answer1', ''),
        data.get('wrong_answer2', ''),
        data.get('wrong_answer3', ''),
        data.get('explanation', '')
    ))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '单选题添加成功'})


@skill_db_bp.route('/api/questions/multi_choice', methods=['POST'])
def add_multi_choice():
    """添加多选题"""
    data = request.json
    group_id = data.get('group_id')
    
    if not group_id:
        return jsonify({'success': False, 'message': '请选择分组'})
    
    options = data.get('options', [])
    correct_answers = data.get('correct_answers', [])
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO multi_choice_questions 
        (group_id, question, correct_answers, answer_options, explanation)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        group_id,
        data.get('question', ''),
        json.dumps(correct_answers, ensure_ascii=False),
        json.dumps(options, ensure_ascii=False),
        data.get('explanation', '')
    ))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '多选题添加成功'})


@skill_db_bp.route('/api/questions/fill_in', methods=['POST'])
def add_fill_in():
    """添加填空题"""
    data = request.json
    group_id = data.get('group_id')
    
    if not group_id:
        return jsonify({'success': False, 'message': '请选择分组'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO fill_in_questions 
        (group_id, question, answer, explanation)
        VALUES (?, ?, ?, ?)
    ''', (
        group_id,
        data.get('question', ''),
        data.get('answer', ''),
        data.get('explanation', '')
    ))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '填空题添加成功'})


@skill_db_bp.route('/api/questions/short_answer', methods=['POST'])
def add_short_answer():
    """添加简答题"""
    data = request.json
    group_id = data.get('group_id')
    
    if not group_id:
        return jsonify({'success': False, 'message': '请选择分组'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO short_answer_questions 
        (group_id, question, answer)
        VALUES (?, ?, ?)
    ''', (
        group_id,
        data.get('question', ''),
        data.get('answer', '')
    ))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '简答题添加成功'})


@skill_db_bp.route('/api/questions/application', methods=['POST'])
def add_application():
    """添加应用题"""
    data = request.json
    group_id = data.get('group_id')
    
    if not group_id:
        return jsonify({'success': False, 'message': '请选择分组'})
    
    sub_questions = data.get('sub_questions', [])
    sub_answers = data.get('sub_answers', [])
    sub_explanations = data.get('sub_explanations', [])
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO application_questions 
        (group_id, scenario, sub_questions, sub_answers, sub_explanations, explanation)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        group_id,
        data.get('scenario', ''),
        json.dumps(sub_questions, ensure_ascii=False),
        json.dumps(sub_answers, ensure_ascii=False),
        json.dumps(sub_explanations, ensure_ascii=False),
        data.get('explanation', '')
    ))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '应用题添加成功'})


@skill_db_bp.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """删除题目"""
    question_type = request.args.get('type', 'single_choice')
    
    table_map = {
        'single_choice': 'single_choice_questions',
        'multi_choice': 'multi_choice_questions',
        'fill_in': 'fill_in_questions',
        'short_answer': 'short_answer_questions',
        'application': 'application_questions'
    }
    
    table_name = table_map.get(question_type)
    if not table_name:
        return jsonify({'success': False, 'message': '无效的题型'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (question_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '题目删除成功'})


# ==================== 导入导出功能 ====================

@skill_db_bp.route('/api/export/group/<int:group_id>', methods=['GET'])
def export_group_excel(group_id):
    """导出分组到Excel"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.name as category_name, g.name as group_name
        FROM question_groups g
        JOIN question_categories c ON g.category_id = c.id
        WHERE g.id = ?
    ''', (group_id,))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'success': False, 'message': '分组不存在'})
    
    category_name = result['category_name']
    group_name = result['group_name']
    
    filename = f"{category_name}_{group_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join('skill_exports', filename)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df_single = pd.read_sql_query(
            'SELECT question as 题目, correct_answer as 正确答案, wrong_answer1 as 混淆答案1, wrong_answer2 as 混淆答案2, wrong_answer3 as 混淆答案3, explanation as 解析 FROM single_choice_questions WHERE group_id = ?',
            conn, params=(group_id,)
        )
        if not df_single.empty:
            df_single.to_excel(writer, sheet_name='单选题', index=False)
        
        df_multi = pd.read_sql_query(
            'SELECT question as 题目, correct_answers as 正确答案, answer_options as 选项列表, explanation as 解析 FROM multi_choice_questions WHERE group_id = ?',
            conn, params=(group_id,)
        )
        if not df_multi.empty:
            df_multi.to_excel(writer, sheet_name='多选题', index=False)
        
        df_fill = pd.read_sql_query(
            'SELECT question as 题目, answer as 答案, explanation as 解析 FROM fill_in_questions WHERE group_id = ?',
            conn, params=(group_id,)
        )
        if not df_fill.empty:
            df_fill.to_excel(writer, sheet_name='填空题', index=False)
        
        df_short = pd.read_sql_query(
            'SELECT question as 题目, answer as 答案 FROM short_answer_questions WHERE group_id = ?',
            conn, params=(group_id,)
        )
        if not df_short.empty:
            df_short.to_excel(writer, sheet_name='简答题', index=False)
        
        df_app = pd.read_sql_query(
            'SELECT scenario as 题干, sub_questions as 小题列表, sub_answers as 答案列表, sub_explanations as 解析列表, explanation as 解析 FROM application_questions WHERE group_id = ?',
            conn, params=(group_id,)
        )
        if not df_app.empty:
            df_app.to_excel(writer, sheet_name='应用题', index=False)
    
    conn.close()
    
    return send_file(filepath, as_attachment=True, download_name=filename)


@skill_db_bp.route('/api/import/excel', methods=['POST'])
def import_excel():
    """导入Excel文件"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '请选择文件'})
    
    file = request.files['file']
    category_name = request.form.get('category_name', '').strip()
    group_name = request.form.get('group_name', '').strip()
    
    if not file.filename:
        return jsonify({'success': False, 'message': '请选择文件'})
    
    if not category_name or not group_name:
        return jsonify({'success': False, 'message': '请输入分类名和分组名'})
    
    temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{uuid.uuid4().hex}.xlsx")
    file.save(temp_path)
    
    xls = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM question_categories WHERE name = ?', (category_name,))
        category = cursor.fetchone()
        
        if category:
            category_id = category['id']
        else:
            cursor.execute(
                'INSERT INTO question_categories (name, description) VALUES (?, ?)',
                (category_name, f'从Excel导入 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            )
            category_id = cursor.lastrowid
        
        cursor.execute(
            'SELECT id FROM question_groups WHERE category_id = ? AND name = ?',
            (category_id, group_name)
        )
        group = cursor.fetchone()
        
        if group:
            group_id = group['id']
        else:
            cursor.execute(
                'INSERT INTO question_groups (category_id, name, description) VALUES (?, ?, ?)',
                (category_id, group_name, f'从Excel导入 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            )
            group_id = cursor.lastrowid
        
        xls = pd.ExcelFile(temp_path)
        stats = {'single_choice': 0, 'multi_choice': 0, 'fill_in': 0, 'short_answer': 0, 'application': 0}
        
        if '单选题' in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name='单选题')
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO single_choice_questions 
                    (group_id, question, correct_answer, wrong_answer1, wrong_answer2, wrong_answer3, explanation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    group_id,
                    str(row.get('题目', '')),
                    str(row.get('正确答案', '')),
                    str(row.get('混淆答案1', '')),
                    str(row.get('混淆答案2', '')),
                    str(row.get('混淆答案3', '')),
                    str(row.get('解析', ''))
                ))
                stats['single_choice'] += 1
        
        # 导入多选题
        if '多选题' in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name='多选题')
            for _, row in df.iterrows():
                correct_ans_str = str(row.get('正确答案', '[]'))
                options_str = str(row.get('选项列表', '[]'))
                
                # 尝试解析，确保是有效的JSON数组
                try:
                    correct_ans = json.loads(correct_ans_str)
                    if not isinstance(correct_ans, list):
                        correct_ans = [correct_ans_str]
                except:
                    correct_ans = [x.strip() for x in correct_ans_str.strip('[]').split(',') if x.strip()]
                
                try:
                    options = json.loads(options_str)
                    if not isinstance(options, list):
                        options = [options_str]
                except:
                    options = [x.strip() for x in options_str.strip('[]').split(',') if x.strip()]
                
                cursor.execute('''
                    INSERT INTO multi_choice_questions 
                    (group_id, question, correct_answers, answer_options, explanation)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    group_id,
                    str(row.get('题目', '')),
                    json.dumps(correct_ans, ensure_ascii=False),
                    json.dumps(options, ensure_ascii=False),
                    str(row.get('解析', ''))
                ))
                stats['multi_choice'] += 1
        
        if '填空题' in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name='填空题')
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO fill_in_questions 
                    (group_id, question, answer, explanation)
                    VALUES (?, ?, ?, ?)
                ''', (
                    group_id,
                    str(row.get('题目', '')),
                    str(row.get('答案', '')),
                    str(row.get('解析', ''))
                ))
                stats['fill_in'] += 1
        
        if '简答题' in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name='简答题')
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO short_answer_questions 
                    (group_id, question, answer)
                    VALUES (?, ?, ?)
                ''', (
                    group_id,
                    str(row.get('题目', '')),
                    str(row.get('答案', ''))
                ))
                stats['short_answer'] += 1
        
        if '应用题' in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name='应用题')
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO application_questions 
                    (group_id, scenario, sub_questions, sub_answers, sub_explanations, explanation)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    group_id,
                    str(row.get('题干', '')),
                    str(row.get('小题列表', '[]')),
                    str(row.get('答案列表', '[]')),
                    str(row.get('解析列表', '[]')),
                    str(row.get('解析', ''))
                ))
                stats['application'] += 1
        
        conn.commit()
        xls.close()
        xls = None
        conn.close()
        
        import time
        time.sleep(0.5)
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': f'导入成功！单选题:{stats["single_choice"]}, 多选题:{stats["multi_choice"]}, 填空题:{stats["fill_in"]}, 简答题:{stats["short_answer"]}, 应用题:{stats["application"]}',
            'stats': stats
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        try:
            if xls is not None:
                xls.close()
        except:
            pass
        
        import time
        time.sleep(0.5)
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'})


# ==================== 资料库管理API ====================

@skill_db_bp.route('/api/resource/files', methods=['GET'])
def get_resource_files():
    """获取资料库文件列表"""
    search = request.args.get('search', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if search:
        cursor.execute('''
            SELECT id, original_name, file_type, file_size, uploader, upload_time, description
            FROM resource_files
            WHERE original_name LIKE ? OR uploader LIKE ? OR description LIKE ?
            ORDER BY upload_time DESC
        ''', (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cursor.execute('''
            SELECT id, original_name, file_type, file_size, uploader, upload_time, description
            FROM resource_files
            ORDER BY upload_time DESC
        ''')
    
    files = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'data': files})


@skill_db_bp.route('/api/resource/upload', methods=['POST'])
def upload_resource_file():
    """上传文件到资料库"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '请选择文件'})
    
    file = request.files['file']
    uploader = request.form.get('uploader', '')
    description = request.form.get('description', '')
    
    if not file.filename:
        return jsonify({'success': False, 'message': '请选择文件'})
    
    if not uploader:
        return jsonify({'success': False, 'message': '请输入上传者姓名'})
    
    # ⭐ 保留中文文件名，只过滤危险字符
    original_name = file.filename
    # 移除路径分隔符等危险字符
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        original_name = original_name.replace(char, '_')
    
    file_ext = os.path.splitext(original_name)[1].lower()
    file_type = file_ext[1:].upper() if file_ext else '未知'
    
    # 生成存储文件名
    new_filename = original_name
    file_path = os.path.join(UPLOAD_FOLDER, new_filename)
    
    # 同名加序号
    if os.path.exists(file_path):
        base, ext = os.path.splitext(original_name)
        counter = 1
        while True:
            new_filename = f"{base}({counter}){ext}"
            file_path = os.path.join(UPLOAD_FOLDER, new_filename)
            if not os.path.exists(file_path):
                break
            counter += 1
    
    file.save(file_path)
    file_size = os.path.getsize(file_path)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO resource_files (filename, original_name, file_type, file_size, uploader, description, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (new_filename, original_name, file_type, file_size, uploader, description, file_path))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'文件上传成功: {original_name}'})


@skill_db_bp.route('/api/resource/download/<int:file_id>', methods=['GET'])
def download_resource_file(file_id):
    """下载文件"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_path, original_name FROM resource_files WHERE id = ?', (file_id,))
    file_info = cursor.fetchone()
    conn.close()
    
    if not file_info:
        return jsonify({'success': False, 'message': '文件不存在'})
    
    file_path = file_info['file_path']
    original_name = file_info['original_name']
    
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    
    return send_file(file_path, as_attachment=True, download_name=original_name)


@skill_db_bp.route('/api/resource/delete/<int:file_id>', methods=['DELETE'])
def delete_resource_file(file_id):
    """删除文件"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_path FROM resource_files WHERE id = ?', (file_id,))
    file_info = cursor.fetchone()
    
    if file_info and os.path.exists(file_info['file_path']):
        os.remove(file_info['file_path'])
    
    cursor.execute('DELETE FROM resource_files WHERE id = ?', (file_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '文件删除成功'})