# recitation_web.py - 单词背诵网页版
from flask import Blueprint, render_template, request, jsonify
import sqlite3
import random
import re

recitation_bp = Blueprint('recitation', __name__)
DB_PATH = "vocabulary.db"


def get_all_groups():
    """获取所有单词组"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT group_name FROM word_groups ORDER BY created_time DESC")
    groups = [row[0] for row in cursor.fetchall()]
    conn.close()
    return groups


def get_group_words(group_name):
    """获取指定组的单词"""
    if not group_name:
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.word, w.part_of_speech, w.chinese_meaning
        FROM words w
        JOIN word_groups wg ON w.group_id = wg.id
        WHERE wg.group_name = ?
    ''', (group_name,))
    words = []
    for row in cursor.fetchall():
        words.append({
            'word': row[0],
            'part_of_speech': row[1],
            'chinese_meaning': row[2].replace('\n', ' ').replace('\r', ' '),
            'group': group_name
        })
    conn.close()
    return words


def check_answer(user_answer, correct_answer):
    """检查答案是否正确"""
    if not user_answer or not correct_answer:
        return False
    
    def clean_text(text):
        text = text.replace('的', '').replace('地', '')
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        return text
    
    user_clean = clean_text(user_answer)
    correct_clean = clean_text(correct_answer)
    
    if len(user_clean) < 2 or len(correct_clean) < 2:
        return False
    
    common_chars = set(user_clean) & set(correct_clean)
    return len(common_chars) >= 2


# ==================== 页面 ====================

@recitation_bp.route('/recitation')
def recitation_page():
    """单词背诵页面"""
    groups = get_all_groups()
    return render_template('recitation.html', groups=groups)


# ==================== API ====================

@recitation_bp.route('/api/recitation/groups')
def api_groups():
    """获取所有单词组"""
    return jsonify(get_all_groups())


@recitation_bp.route('/api/recitation/words')
def api_words():
    """获取单词"""
    today_group = request.args.get('today', '')
    yesterday_group = request.args.get('yesterday', '')
    shuffle = request.args.get('shuffle', 'false').lower() == 'true'
    
    words = []
    if today_group:
        today_words = get_group_words(today_group)
        for w in today_words:
            w['type'] = '今日'
        words.extend(today_words)
    
    if yesterday_group:
        yesterday_words = get_group_words(yesterday_group)
        for w in yesterday_words:
            w['type'] = '昨日'
        words.extend(yesterday_words)
    
    if shuffle:
        random.shuffle(words)
    
    return jsonify({
        'words': words,
        'total': len(words),
        'today_group': today_group,
        'yesterday_group': yesterday_group
    })


@recitation_bp.route('/api/recitation/check', methods=['POST'])
def api_check():
    """批量检查答案"""
    data = request.get_json()
    answers = data.get('answers', [])
    
    results = []
    correct_count = 0
    
    for item in answers:
        user_answer = item.get('user_answer', '')
        correct_answer = item.get('correct_answer', '')
        is_correct = check_answer(user_answer, correct_answer)
        if is_correct:
            correct_count += 1
        results.append({
            'word': item.get('word', ''),
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct
        })
    
    return jsonify({
        'results': results,
        'correct_count': correct_count,
        'total': len(answers),
        'accuracy': round(correct_count / len(answers) * 100, 1) if answers else 0
    })