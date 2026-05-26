# nightmare_exam_web.py
from flask import Blueprint, render_template, request, jsonify, session
import sqlite3
import json
import random
from difflib import SequenceMatcher

nightmare_bp = Blueprint('nightmare', __name__, url_prefix='/nightmare')
DATABASE = 'skill_database.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@nightmare_bp.route('/')
def nightmare_page():
    return render_template('nightmare_exam.html', user_name=session.get('user_name', '未登录'))


# ==================== 获取分类和统计 ====================

@nightmare_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有分类及题目统计"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM question_categories ORDER BY name')
    categories = []
    for row in cursor.fetchall():
        cat = dict(row)
        cursor.execute('SELECT id FROM question_groups WHERE category_id = ?', (cat['id'],))
        group_ids = [g['id'] for g in cursor.fetchall()]
        stats = get_category_stats(cursor, group_ids)
        cat['stats'] = stats
        categories.append(cat)
    conn.close()
    return jsonify({'success': True, 'data': categories})


def get_category_stats(cursor, group_ids):
    """获取分类下各题型数量"""
    if not group_ids:
        return {'single': 0, 'multi': 0, 'fill': 0, 'short': 0, 'application': 0}
    
    placeholders = ','.join(['?'] * len(group_ids))
    stats = {}
    
    for qtype, table in [
        ('single', 'single_choice_questions'),
        ('multi', 'multi_choice_questions'),
        ('fill', 'fill_in_questions'),
        ('short', 'short_answer_questions'),
    ]:
        cursor.execute(f'SELECT COUNT(*) as cnt FROM {table} WHERE group_id IN ({placeholders})', group_ids)
        stats[qtype] = cursor.fetchone()['cnt']
    
    # 应用题：统计所有大题的 sub_questions 小问总数
    cursor.execute(f'SELECT sub_questions FROM application_questions WHERE group_id IN ({placeholders})', group_ids)
    total_sub = 0
    for row in cursor.fetchall():
        if row['sub_questions']:
            try:
                subs = json.loads(row['sub_questions'])
                total_sub += len(subs)
            except:
                pass
    stats['application'] = total_sub
    
    return stats


# ==================== 组卷 ====================

@nightmare_bp.route('/api/generate_exam', methods=['POST'])
def generate_exam():
    """生成试卷"""
    data = request.json
    category_id = data.get('category_id')
    question_counts = data.get('question_counts', {})
    pass_score = data.get('pass_score', 60)
    exam_time = data.get('exam_time', 120)
    total_score = data.get('total_score', 100)  # ⭐ 用户设置的总分
    
    if not category_id:
        return jsonify({'success': False, 'message': '请选择分类'})
    
    n1 = int(question_counts.get('single', 0))
    n2 = int(question_counts.get('multi', 0))
    n3 = int(question_counts.get('fill', 0))
    n4 = int(question_counts.get('short', 0))
    n5 = int(question_counts.get('application', 0))  # ⭐ 大题数量
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM question_groups WHERE category_id = ?', (category_id,))
    group_ids = [g['id'] for g in cursor.fetchall()]
    
    if not group_ids:
        conn.close()
        return jsonify({'success': False, 'message': '该分类下没有分组'})
    
    placeholders = ','.join(['?'] * len(group_ids))
    
    # 收集题目
    all_questions = {'single': [], 'multi': [], 'fill': [], 'short': [], 'application': []}
    
    cursor.execute(f'SELECT id, question, correct_answer, wrong_answer1, wrong_answer2, wrong_answer3, explanation FROM single_choice_questions WHERE group_id IN ({placeholders})', group_ids)
    all_questions['single'] = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute(f'SELECT id, question, correct_answers, answer_options, explanation FROM multi_choice_questions WHERE group_id IN ({placeholders})', group_ids)
    for row in cursor.fetchall():
        q = dict(row)
        try:
            q['correct_answers'] = json.loads(q['correct_answers']) if q['correct_answers'] else []
            q['answer_options'] = json.loads(q['answer_options']) if q['answer_options'] else []
        except:
            q['correct_answers'] = []
            q['answer_options'] = []
        all_questions['multi'].append(q)
    
    cursor.execute(f'SELECT id, question, answer, explanation FROM fill_in_questions WHERE group_id IN ({placeholders})', group_ids)
    all_questions['fill'] = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute(f'SELECT id, question, answer FROM short_answer_questions WHERE group_id IN ({placeholders})', group_ids)
    all_questions['short'] = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute(f'SELECT id, scenario, sub_questions, sub_answers, sub_explanations, explanation FROM application_questions WHERE group_id IN ({placeholders})', group_ids)
    for row in cursor.fetchall():
        q = dict(row)
        try:
            q['sub_questions'] = json.loads(q['sub_questions']) if q['sub_questions'] else []
            q['sub_answers'] = json.loads(q['sub_answers']) if q['sub_answers'] else []
            q['sub_explanations'] = json.loads(q['sub_explanations']) if q['sub_explanations'] else []
        except:
            q['sub_questions'] = []
            q['sub_answers'] = []
            q['sub_explanations'] = []
        all_questions['application'].append(q)
    
    conn.close()
    
    # 检查题目是否足够
    available = {
        'single': len(all_questions['single']),
        'multi': len(all_questions['multi']),
        'fill': len(all_questions['fill']),
        'short': len(all_questions['short']),
        'application': len(all_questions['application'])  # 大题数量
    }
    
    checks = [
        ('single', n1, '单选题'),
        ('multi', n2, '多选题'),
        ('fill', n3, '填空题'),
        ('short', n4, '简答题'),
        ('application', n5, '应用大题'),
    ]
    for key, need, name in checks:
        if need > 0 and available[key] < need:
            return jsonify({'success': False, 'message': f'{name}不足，需要{need}道，题库只有{available[key]}道'})
    
    # 随机选择题目
    selected = {
        'single': random.sample(all_questions['single'], n1) if n1 > 0 else [],
        'multi': random.sample(all_questions['multi'], n2) if n2 > 0 else [],
        'fill': random.sample(all_questions['fill'], n3) if n3 > 0 else [],
        'short': random.sample(all_questions['short'], n4) if n4 > 0 else [],
    }
    
    # ⭐ 随机抽取大题，展开所有小问
    selected_apps = random.sample(all_questions['application'], n5) if n5 > 0 else []
    selected['application'] = []
    for app in selected_apps:
        for i, sub_q in enumerate(app['sub_questions']):
            selected['application'].append({
                'parent_id': app['id'],
                'parent_scenario': app['scenario'],
                'sub_index': i,
                'sub_question': sub_q,
                'sub_answer': app['sub_answers'][i] if i < len(app['sub_answers']) else '',
                'sub_explanation': app['sub_explanations'][i] if i < len(app['sub_explanations']) else '',
                'parent_explanation': app.get('explanation', '')
            })
    
    # ⭐ 计算实际小问数，重新算分数
    actual_app_subs = len(selected['application'])
    
    # 按比例算分：单选:多选:填空:简答:应用小问 = 2:2:2:5:5
    denominator = 2*n1 + 2*n2 + 2*n3 + 5*n4 + 5*actual_app_subs
    if denominator == 0:
        return jsonify({'success': False, 'message': '请至少设置一道题目'})
    
    x = total_score / denominator
    
    score_per_question = {
        'single': round(2 * x, 2),
        'multi': round(2 * x, 2),
        'fill': round(2 * x, 2),
        'short': round(5 * x, 2),
        'application_sub': round(5 * x, 2)
    }
    
    # 返回给前端
    frontend_data = {
        'success': True,
        'config': {
            'question_counts': {'single': n1, 'multi': n2, 'fill': n3, 'short': n4, 'application': actual_app_subs},
            'scores': score_per_question,
            'pass_score': pass_score,
            'exam_time': exam_time * 60,
            'total_score': total_score,
        },
        'questions': format_questions_for_frontend(selected),
    }
    
    return jsonify(frontend_data)


def select_application_subquestions(app_questions, needed):
    """从应用题中选取小问"""
    all_subs = []
    for q in app_questions:
        for i, sub_q in enumerate(q['sub_questions']):
            all_subs.append({
                'parent_id': q['id'],
                'parent_scenario': q['scenario'],
                'sub_index': i,
                'sub_question': sub_q,
                'sub_answer': q['sub_answers'][i] if i < len(q['sub_answers']) else '',
                'sub_explanation': q['sub_explanations'][i] if i < len(q['sub_explanations']) else '',
                'parent_explanation': q.get('explanation', '')
            })
    
    if len(all_subs) <= needed:
        return all_subs
    return random.sample(all_subs, needed)


def format_questions_for_frontend(selected):
    """格式化题目给前端（考试用，含选项但不含答案）"""
    result = {'single': [], 'multi': [], 'fill': [], 'short': [], 'application': []}
    
    for q in selected['single']:
        correct = q['correct_answer']
        wrongs = [q.get('wrong_answer1', ''), q.get('wrong_answer2', ''), q.get('wrong_answer3', '')]
        wrongs = [w for w in wrongs if w]
        options = [correct] + wrongs
        random.shuffle(options)
        result['single'].append({
            'id': q['id'],
            'question': q['question'],
            'options': options,
            'correct_answer': correct,  # 保留正确答案用于前端批改
            'explanation': q.get('explanation', '')
        })
    
    for q in selected['multi']:
        options = q.get('answer_options', [])
        corrects = q.get('correct_answers', [])
        shuffled = options.copy()
        random.shuffle(shuffled)
        result['multi'].append({
            'id': q['id'],
            'question': q['question'],
            'options': shuffled,
            'correct_answers': corrects,
            'explanation': q.get('explanation', '')
        })
    
    for q in selected['fill']:
        result['fill'].append({
            'id': q['id'],
            'question': q['question'],
            'correct_answer': q.get('answer', ''),
            'explanation': q.get('explanation', '')
        })
    
    for q in selected['short']:
        result['short'].append({
            'id': q['id'],
            'question': q['question'],
            'correct_answer': q.get('answer', '')
        })
    
    for sub in selected['application']:
        result['application'].append({
            'parent_id': sub['parent_id'],
            'scenario': sub['parent_scenario'],
            'sub_index': sub['sub_index'],
            'sub_question': sub['sub_question'],
            'correct_answer': sub['sub_answer'],
            'explanation': sub.get('sub_explanation', '')
        })
    
    return result


def format_answer_key(selected):
    """仅返回正确答案映射"""
    key = {'single': [], 'multi': [], 'fill': [], 'short': [], 'application': []}
    for q in selected['single']:
        key['single'].append({'id': q['id'], 'answer': q['correct_answer']})
    for q in selected['multi']:
        key['multi'].append({'id': q['id'], 'answer': q.get('correct_answers', [])})
    for q in selected['fill']:
        key['fill'].append({'id': q['id'], 'answer': q.get('answer', '')})
    for q in selected['short']:
        key['short'].append({'id': q['id'], 'answer': q.get('answer', '')})
    for sub in selected['application']:
        key['application'].append({'parent_id': sub['parent_id'], 'sub_index': sub['sub_index'], 'answer': sub['sub_answer']})
    return key


# ==================== 提交批改 ====================

@nightmare_bp.route('/api/submit', methods=['POST'])
def submit_exam():
    """提交试卷并批改 - 前端传递题目数据"""
    data = request.json
    user_answers = data.get('answers', {})
    exam_questions = data.get('questions', {})
    scores = data.get('scores', {})
    pass_score = data.get('pass_score', 60)
    
    if not exam_questions:
        return jsonify({'success': False, 'message': '题目数据缺失，请重新组卷'})
    
    grading_result = {
        'single': [], 'multi': [], 'fill': [], 'short': [], 'application': [],
        'total_score': 0
    }
    
    # ==================== 批改单选题 ====================
    for i, q in enumerate(exam_questions.get('single', [])):
        user_idx_str = user_answers.get('single', {}).get(str(i), '-1')
        options = q.get('options', [])
        correct = q.get('correct_answer', '')
        
        try:
            user_idx = int(user_idx_str)
            user_selected = options[user_idx] if 0 <= user_idx < len(options) else ''
        except:
            user_selected = ''
        
        is_correct = (user_selected == correct)
        score = scores.get('single', 0) if is_correct else 0
        grading_result['total_score'] += score
        
        grading_result['single'].append({
            'id': q['id'],
            'question': q['question'],
            'options': options,
            'correct_answer': correct,
            'user_selected': user_selected,
            'is_correct': is_correct,
            'score': score,
            'full_score': scores.get('single', 0),
            'explanation': q.get('explanation', '')
        })
    
    # ==================== 批改多选题 ====================
    for i, q in enumerate(exam_questions.get('multi', [])):
        user_indices_str = user_answers.get('multi', {}).get(str(i), '')
        try:
            user_indices = [int(x) for x in user_indices_str.split(',') if x.strip()]
        except:
            user_indices = []
        
        options = q.get('options', [])
        corrects = set(q.get('correct_answers', []))
        user_selected = set(options[j] for j in user_indices if 0 <= j < len(options))
        
        if user_selected == corrects:
            is_correct = True
            score = scores.get('multi', 0)
        elif user_selected and user_selected.issubset(corrects):
            is_correct = 'partial'
            score = round(scores.get('multi', 0) / 2, 2)
        else:
            is_correct = False
            score = 0
        
        grading_result['total_score'] += score
        
        grading_result['multi'].append({
            'id': q['id'],
            'question': q['question'],
            'options': options,
            'correct_answers': list(corrects),
            'user_selected': list(user_selected),
            'is_correct': is_correct,
            'score': score,
            'full_score': scores.get('multi', 0),
            'explanation': q.get('explanation', '')
        })
    
    # ==================== 批改填空题 ====================
    for i, q in enumerate(exam_questions.get('fill', [])):
        user_ans = user_answers.get('fill', {}).get(str(i), '')
        correct = q.get('correct_answer', '')
        similarity = SequenceMatcher(None, user_ans.lower(), correct.lower()).ratio() if user_ans and correct else 0
        
        full = scores.get('fill', 0)
        if similarity >= 0.8:
            score = full
            is_correct = True
        elif similarity > 0:
            score = round(full * (similarity / 0.8), 2)
            is_correct = 'partial'
        else:
            score = 0
            is_correct = False
        
        grading_result['total_score'] += score
        
        grading_result['fill'].append({
            'id': q['id'],
            'question': q['question'],
            'correct_answer': correct,
            'user_answer': user_ans,
            'similarity': round(similarity, 2),
            'is_correct': is_correct,
            'score': score,
            'full_score': full,
            'explanation': q.get('explanation', '')
        })
    
    # ==================== 批改简答题 ====================
    for i, q in enumerate(exam_questions.get('short', [])):
        user_ans = user_answers.get('short', {}).get(str(i), '')
        correct = q.get('correct_answer', '')
        similarity = SequenceMatcher(None, user_ans.lower(), correct.lower()).ratio() if user_ans and correct else 0
        
        full = scores.get('short', 0)
        if similarity >= 0.8:
            score = full
            is_correct = True
        elif similarity > 0:
            score = round(full * (similarity / 0.8), 2)
            is_correct = 'partial'
        else:
            score = 0
            is_correct = False
        
        grading_result['total_score'] += score
        
        grading_result['short'].append({
            'id': q['id'],
            'question': q['question'],
            'correct_answer': correct,
            'user_answer': user_ans,
            'similarity': round(similarity, 2),
            'is_correct': is_correct,
            'score': score,
            'full_score': full
        })
    
    # ==================== 批改应用题 ====================
    for i, q in enumerate(exam_questions.get('application', [])):
        user_ans = user_answers.get('application', {}).get(str(i), '')
        correct = q.get('correct_answer', '')
        similarity = SequenceMatcher(None, user_ans.lower(), correct.lower()).ratio() if user_ans and correct else 0
        
        full = scores.get('application_sub', 0)
        if similarity >= 0.8:
            score = full
            is_correct = True
        elif similarity > 0:
            score = round(full * (similarity / 0.8), 2)
            is_correct = 'partial'
        else:
            score = 0
            is_correct = False
        
        grading_result['total_score'] += score
        
        grading_result['application'].append({
            'parent_id': q.get('parent_id'),
            'scenario': q.get('scenario', ''),
            'sub_index': q.get('sub_index', 0),
            'sub_question': q.get('sub_question', ''),
            'correct_answer': correct,
            'user_answer': user_ans,
            'similarity': round(similarity, 2),
            'is_correct': is_correct,
            'score': score,
            'full_score': full,
            'explanation': q.get('explanation', '')
        })
    
    grading_result['total_score'] = round(grading_result['total_score'], 2)
    grading_result['pass_score'] = pass_score
    grading_result['passed'] = grading_result['total_score'] >= pass_score
    grading_result['scores'] = scores
    
    return jsonify({'success': True, 'result': grading_result})