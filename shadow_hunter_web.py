# shadow_hunter_web.py - 阴影迷踪网页版（完整版）
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from exam_base_web import prepare_basic_words, get_all_group_names, calculate_similarity
from vocabulary_manager import get_vocab_manager
from exam_stats_db import get_exam_stats_db
import random, os, uuid, json, sqlite3, re, difflib, math, threading
from ai_correct import ai_corrector
from settings_web import get_all_settings
from shadow_exam_web import (
    prepare_shadow_words as prepare_shadow_words_by_place,
    calc_shadow_score,
    PLACE_NAMES,
    PLACE_WEIGHTS,
)
from seventy_two_web import (
    prepare_strategy_words as prepare_strategy_words_72_full,
    build_meaning_options as build_meaning_options_72_full,
)
from thirty_six_web import prepare_strategy_words as prepare_strategy_words_36_full
from treasure_web import (
    prepare_treasure_words,
    generate_treasure_answers,
    generate_wrong_meanings_for_web,
    build_words_pool,
)
from vocabulary_manager import VocabularyManager
shadow_hunter_bp = Blueprint('shadow_hunter', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@shadow_hunter_bp.before_request
def require_login():
    if 'user' not in session:
        session['next_url'] = request.url
        return redirect(url_for('login'))


def get_stats_db():
    return get_exam_stats_db()

PATTERN_PASS_SCORES = {"盗宝大师": 46, "诡影重重": 45, "三十六计": 47, "七十二变": 47, "阴影迷踪": 45}
FULL_SCORE = 50
BASIC_FULL = 30
PATTERNS = ["三十六计", "七十二变", "诡影重重", "盗宝大师"]
PATTERN_WEIGHTS = [1, 1, 1, 1]
TREASURE_NAMES = ['青山', '寒山', '沧山', '暮山', '尘山']

exam_sessions = {}


def _prepare_pattern(es, pattern_name):
    """后台预准备单个版型的出题数据"""
    today, yesterday = es['today'], es['yesterday']
    try:
        if pattern_name == '三十六计':
            strategy_data, error = None, '出题失败'
            for _ in range(5):
                strategy_data, error = prepare_strategy_words_36_full(today, yesterday)
                if not error:
                    break
            if error:
                return {'ready': False, 'error': error, 'data': None}
            return {'ready': True, 'error': None, 'data': strategy_data}

        if pattern_name == '七十二变':
            suffix_words, similar_words, suffix_extra, similar_extra, error = prepare_strategy_words_72_full(
                today, yesterday
            )
            if error:
                return {'ready': False, 'error': error, 'data': None}
            suffix_meanings = build_meaning_options_72_full(suffix_words, suffix_extra or [])
            similar_meanings = build_meaning_options_72_full(similar_words, similar_extra or [])
            return {
                'ready': True, 'error': None,
                'data': {
                    'suffix_words': suffix_words,
                    'similar_words': similar_words,
                    'suffix_meanings': suffix_meanings,
                    'similar_meanings': similar_meanings,
                },
            }

        if pattern_name == '诡影重重':
            place = random.choices(PLACE_NAMES, weights=PLACE_WEIGHTS, k=1)[0]
            shadow_words, place, error = prepare_shadow_words_by_place(today, yesterday, place)
            if error:
                return {'ready': False, 'error': error, 'data': None}
            return {
                'ready': True, 'error': None,
                'data': {
                    'selected_place': place,
                    'shadow_words': [
                        {'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning']}
                        for w in shadow_words
                    ],
                },
            }

        if pattern_name == '盗宝大师':
            treasure_words, error = prepare_treasure_words(today, yesterday)
            if error:
                return {'ready': False, 'error': error, 'data': None}
            words_pool = build_words_pool()
            answers, meanings, true_treasure, treasure_counts = generate_treasure_answers(treasure_words)
            return {
                'ready': True, 'error': None,
                'data': {
                    'treasure_words_raw': treasure_words,
                    'treasure_words': [
                        {'word': w['word'], 'pos': w.get('part_of_speech', ''), 'meaning': w.get('chinese_meaning', '')}
                        for w in treasure_words
                    ],
                    'treasure_answers': answers,
                    'treasure_meanings': meanings,
                    'true_treasure': true_treasure,
                    'treasure_counts': treasure_counts,
                    'words_pool': words_pool,
                },
            }
    except Exception as e:
        return {'ready': False, 'error': str(e), 'data': None}
    return {'ready': False, 'error': '未知版型', 'data': None}


def _apply_pattern_cache(es):
    """将预准备的版型题目写入会话"""
    pattern_name = es.get('selected_pattern') or es.get('predetermined_pattern')
    prep = es.get('pattern_prep') or {}
    if not prep.get('ready') or not prep.get('data'):
        return False
    data = prep['data']

    if pattern_name == '三十六计':
        es['meanings_36'] = data['meanings']
        es['card_pool_36'] = data['card_pool']
        es['hand_cards_36'] = data['card_pool'][:7]
        es['pool_index_36'] = 7
        es['placements_36'] = {}
    elif pattern_name == '七十二变':
        es['suffix_words'] = data['suffix_words']
        es['similar_words'] = data['similar_words']
        es['suffix_meanings'] = data['suffix_meanings']
        es['similar_meanings'] = data['similar_meanings']
        es['strategy_ready'] = True
    elif pattern_name == '诡影重重':
        es['selected_place'] = data['selected_place']
        es['shadow_words'] = data['shadow_words']
    elif pattern_name == '盗宝大师':
        es['treasure_words'] = data['treasure_words']
        es['treasure_answers'] = data['treasure_answers']
        es['treasure_meanings'] = data['treasure_meanings']
        es['true_treasure'] = data['true_treasure']
        es['treasure_counts'] = data['treasure_counts']
        es['_words_pool'] = data.get('words_pool') or build_words_pool()
    return True


def _ensure_treasure_data(es):
    """确保盗宝大师题目已生成（优先使用预准备缓存）"""
    if es.get('treasure_answers'):
        return None
    if _apply_pattern_cache(es):
        return None
    if es.get('predetermined_pattern') != '盗宝大师':
        return '盗宝大师题目未准备'
    treasure_words, error = prepare_treasure_words(es['today'], es['yesterday'])
    if error:
        return error
    words_pool = build_words_pool()
    answers, meanings, true_treasure, treasure_counts = generate_treasure_answers(treasure_words)
    es['treasure_words'] = [
        {'word': w['word'], 'pos': w.get('part_of_speech', ''), 'meaning': w.get('chinese_meaning', '')}
        for w in treasure_words
    ]
    es['treasure_answers'] = answers
    es['treasure_meanings'] = meanings
    es['true_treasure'] = true_treasure
    es['treasure_counts'] = treasure_counts
    es['_words_pool'] = words_pool
    return None


def _background_prepare_pattern(exam_id, user_id, app):
    from flask import g
    with app.app_context():
        g._vocab_manager = VocabularyManager(user_id=user_id)
        es = exam_sessions.get(exam_id)
        if not es:
            return
        pattern_name = es.get('predetermined_pattern')
        if not pattern_name:
            return
        es['pattern_prep'] = _prepare_pattern(es, pattern_name)
        es['pattern_prep_done'] = True


@shadow_hunter_bp.route('/exam/shadow_hunter')
def shadow_hunter_page():
    settings = get_all_settings()
    return render_template('shadow_hunter.html',
                         groups=get_all_group_names(),
                         patterns=PATTERNS,
                         pattern_pass_scores=PATTERN_PASS_SCORES,
                         full_score=FULL_SCORE,
                         basic_full=BASIC_FULL,
                         place_names=PLACE_NAMES,
                         user_name=settings.get('user_name', ''),
                         student_id=settings.get('student_id', ''))


@shadow_hunter_bp.route('/api/shadow_hunter/start', methods=['POST'])
def start_exam():
    """开始考试 - 准备基础词汇"""
    data = request.get_json()
    today = data.get('today_group', '').strip()
    yesterday = data.get('yesterday_group', '').strip()
    
    if not today or not yesterday:
        return jsonify({'success': False, 'message': '请选择今日和昨日单词组'})
    
    basic_words, error = prepare_basic_words(today, yesterday)
    if error:
        return jsonify({'success': False, 'message': error})
    
    exam_id = str(uuid.uuid4())
    
    # 获取词典名称
    try:
        conn = sqlite3.connect(get_vocab_manager().db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.dict_name FROM dictionaries d
            JOIN word_groups wg ON wg.dict_id = d.id
            WHERE wg.group_name = ?
        ''', (today,))
        result = cursor.fetchone()
        conn.close()
        dictionary_name = result[0] if result else "默认词典"
    except:
        dictionary_name = "默认词典"
    
    predetermined_pattern = random.choices(PATTERNS, weights=PATTERN_WEIGHTS, k=1)[0]

    exam_sessions[exam_id] = {
        'basic': [{'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning']} for w in basic_words],
        'today': today,
        'yesterday': yesterday,
        'dictionary_name': dictionary_name,
        'basic_results': [],
        'basic_score': 0,
        'predetermined_pattern': predetermined_pattern,
        'selected_pattern': None,
        'pattern_prep': {'ready': False, 'error': None, 'data': None},
        'pattern_prep_done': False,
    }
    from flask import current_app
    user_id = session.get('user', {}).get('id')
    app = current_app._get_current_object()
    threading.Thread(target=_background_prepare_pattern, args=(exam_id, user_id, app), daemon=True).start()

    return jsonify({
        'success': True,
        'exam_id': exam_id,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(basic_words)],
        'total': len(basic_words)
    })


@shadow_hunter_bp.route('/api/shadow_hunter/submit_basic', methods=['POST'])
def submit_basic():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    
    answers = data.get('answers', {})
    words = es['basic']
    results = []
    total_score = 0.0
    used_ai = False  # 标记是否使用了AI批改
    
    # ========== 尝试AI批改 ==========
    words_for_ai = []
    for i, w in enumerate(words):
        ua = answers.get(str(i), '').strip()
        if ua:  # 只对已作答的进行AI批改
            words_for_ai.append({
                'word': w['word'],
                'correct_meaning': w['meaning'],
                'user_answer': ua
            })
    
    ai_scores = {}
    if words_for_ai:
        print(f"开始AI批改，单词数: {len(words_for_ai)}")
        ai_result = ai_corrector.correct_batch(words_for_ai)
        print(f"AI批改结果: {ai_result}")
        if ai_result['success'] and ai_result['scores']:
            used_ai = True
            idx = 0
            for i, w in enumerate(words):
                ua = answers.get(str(i), '').strip()
                if ua and idx < len(ai_result['scores']):
                    ai_scores[i] = ai_result['scores'][idx]
                    idx += 1
    
    # ========== 生成结果 ==========
    for i, w in enumerate(words):
        ua = answers.get(str(i), '').strip()
        
        if i in ai_scores and used_ai:
            # 使用AI批改分数
            score = ai_scores[i]
            if score >= 0.99:
                border_color = "#00ff00"
            elif score >= 0.5:
                border_color = "#ffd700"
            elif score >= 0.25:
                border_color = "#ffa500"
            else:
                border_color = "#ff0000"
        else:
            # 使用系统自动批改
            score, border_color = auto_correct_shadow_hunter(ua, w['meaning'])
        
        total_score += score
        results.append({
            'index': i,
            'word': w['word'],
            'pos': w['pos'],
            'meaning': w['meaning'],
            'user_answer': ua,
            'score': round(score, 2),
            'score_display': f"{score:.2f}",
            'border_color': border_color,
            'is_correct': score >= 0.99,
            'used_ai': used_ai  # 标记此结果是否由AI批改
        })
        
    
    es['basic_results'] = results
    es['basic_score'] = round(total_score, 2)
    es['used_ai'] = used_ai
    
    # 更新错题本
    for r in results:
        try:
            if r['score'] >= 1.0:
                get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass
    
    return jsonify({
        'success': True,
        'results': results,
        'score': round(total_score, 2),
        'total': len(words),
        'used_ai': used_ai
    })


@shadow_hunter_bp.route('/api/shadow_hunter/pattern_status', methods=['POST'])
def pattern_status():
    """查询预定版型的预出题是否就绪"""
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    prep = es.get('pattern_prep') or {}
    pattern = es.get('predetermined_pattern') or data.get('pattern', '')
    return jsonify({
        'success': True,
        'pattern': pattern,
        'ready': bool(prep.get('ready')),
        'error': prep.get('error'),
    })


@shadow_hunter_bp.route('/api/shadow_hunter/draw_pattern', methods=['POST'])
def draw_pattern():
    """揭晓预定版型（开始考试时已随机确定）"""
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})

    selected = es.get('predetermined_pattern')
    if not selected:
        return jsonify({'success': False, 'message': '版型未确定'})
    es['selected_pattern'] = selected
    _apply_pattern_cache(es)

    pass_score = PATTERN_PASS_SCORES.get(selected, 46)

    return jsonify({
        'success': True,
        'pattern': selected,
        'basic_score': es['basic_score'],
        'pass_score': pass_score,
        'exam_id': exam_id
    })


def auto_correct_shadow_hunter(user_answer, correct_answer):
    """阴影迷踪自动批改规则：
    过滤的、地、了、是后：
    - 正确答案1字：完全相同=1分
    - 正确答案>1字：≥2个相同=1分，1个相同=0.75分，0个=0分
    """
    if not user_answer:
        return 0.0, "#ff0000"
    
    if not correct_answer:
        return 0.0, "#ff0000"
    
    filter_chars = ['的', '地', '了', '是']
    user_clean = ''.join([c for c in user_answer if c not in filter_chars])
    correct_clean = ''.join([c for c in correct_answer if c not in filter_chars])
    
    if not user_clean or not correct_clean:
        return 0.0, "#ff0000"
    
    if len(correct_clean) == 1:
        if user_clean == correct_clean:
            return 1.0, "#00ff00"
        else:
            return 0.0, "#ff0000"
    else:
        common_count = 0
        for char in set(user_clean):
            if char in correct_clean:
                common_count += min(user_clean.count(char), correct_clean.count(char))
        
        if common_count >= 2:
            return 1.0, "#00ff00"
        elif common_count == 1:
            return 0.75, "#ffd700"
        else:
            return 0.0, "#ff0000"
        
# ========== 诡影重重20分 API（与独立诡影重重版型一致：地名抽取 + 按词性出题） ==========
@shadow_hunter_bp.route('/api/shadow_hunter/shadow_draw_place', methods=['POST'])
def shadow_draw_place():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    prep = es.get('pattern_prep') or {}
    if prep.get('ready') and prep.get('data'):
        selected_place = prep['data']['selected_place']
    elif es.get('selected_place'):
        selected_place = es['selected_place']
    else:
        selected_place = random.choices(PLACE_NAMES, weights=PLACE_WEIGHTS, k=1)[0]
    es['selected_place'] = selected_place
    return jsonify({'success': True, 'place': selected_place})


@shadow_hunter_bp.route('/api/shadow_hunter/shadow_prepare_words', methods=['POST'])
def shadow_prepare_words():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    if es.get('shadow_words') and es.get('selected_place'):
        return jsonify({
            'success': True,
            'place': es['selected_place'],
            'words': [
                {'word': w['word'], 'pos': w['pos'], 'index': i}
                for i, w in enumerate(es['shadow_words'])
            ],
            'total': len(es['shadow_words']),
        })
    selected_place = es.get('selected_place')
    if not selected_place:
        return jsonify({'success': False, 'message': '请先抽取地名'})
    shadow_words, place, error = prepare_shadow_words_by_place(
        es['today'], es['yesterday'], selected_place
    )
    if error:
        return jsonify({'success': False, 'message': error})
    es['shadow_words'] = [
        {'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning']}
        for w in shadow_words
    ]
    return jsonify({
        'success': True,
        'place': place,
        'words': [
            {'word': w['word'], 'pos': w['pos'], 'index': i}
            for i, w in enumerate(es['shadow_words'])
        ],
        'total': len(es['shadow_words']),
    })

@shadow_hunter_bp.route('/api/shadow_hunter/shadow_submit', methods=['POST'])
def shadow_submit():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    answers = data.get('answers', {})
    results, total = [], 0.0
    for i, w in enumerate(es['shadow_words']):
        ua = answers.get(str(i), '').strip()
        sc = calc_shadow_score(ua, w['meaning'])
        total += sc
        results.append({'index': i, 'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning'], 'user_answer': ua, 'score': sc, 'score_display': f"{sc:.2f}"})
    
    final_shadow = min(total, 20.0)
    es['pattern_score'] = final_shadow
    es['pattern_results'] = results
    es['pattern_words_data'] = [
    {
        'word': r['word'],
        'part_of_speech': r.get('pos', ''),
        'meaning': r['meaning'],
        'score': r['score'],
        'score_display': r.get('score_display', f"{r['score']:.2f}")
    }
    for r in results
]
    process_wrong_books_shadow(results)
    
    basic_score = es.get('basic_score', 0)
    total_score = basic_score + final_shadow
    is_passed = total_score >= PATTERN_PASS_SCORES.get('诡影重重', 45)
    
    save_final_record(es, final_shadow)
    
    return jsonify({'success': True, 'results': results, 'shadow_score': final_shadow, 'basic_score': basic_score, 'total_score': total_score, 'is_passed': is_passed})

# ========== 七十二变20分 API ==========
@shadow_hunter_bp.route('/api/shadow_hunter/seventytwo_start', methods=['POST'])
def seventytwo_start():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})

    prep = es.get('pattern_prep') or {}
    if prep.get('ready') and prep.get('data'):
        cached = prep['data']
        suffix_words = cached['suffix_words']
        similar_words = cached['similar_words']
        suffix_meanings = cached['suffix_meanings']
        similar_meanings = cached['similar_meanings']
    elif es.get('suffix_words') and es.get('similar_words'):
        suffix_words = es['suffix_words']
        similar_words = es['similar_words']
        suffix_meanings = es['suffix_meanings']
        similar_meanings = es['similar_meanings']
    else:
        suffix_words, similar_words, suffix_extra, similar_extra, error = prepare_strategy_words_72_full(
            es['today'], es['yesterday']
        )
        if error:
            return jsonify({'success': False, 'message': error})
        suffix_meanings = build_meaning_options_72_full(suffix_words, suffix_extra or [])
        similar_meanings = build_meaning_options_72_full(similar_words, similar_extra or [])

    es['suffix_words'] = suffix_words
    es['similar_words'] = similar_words
    es['suffix_meanings'] = suffix_meanings
    es['similar_meanings'] = similar_meanings
    es['strategy_ready'] = True

    return jsonify({
        'success': True,
        'suffix_words': suffix_words,
        'similar_words': similar_words,
        'suffix_meanings': suffix_meanings,
        'similar_meanings': similar_meanings,
    })

@shadow_hunter_bp.route('/api/shadow_hunter/seventytwo_submit', methods=['POST'])
def seventytwo_submit():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    pairs = data.get('pairs', {})
    all_words = es['suffix_words'] + es['similar_words']
    results, strategy_score = [], 0
    for w in all_words:
        user_meaning = pairs.get(w['id'], '')
        is_correct = user_meaning == w['meaning']
        if is_correct:
            strategy_score += 1
        results.append({
            'id': w['id'], 'word': w['word'], 'pos': w.get('part_of_speech', ''),
            'meaning': w['meaning'], 'user_meaning': user_meaning,
            'is_correct': is_correct, 'score': '1.00' if is_correct else '0.00',
        })
        try:
            if is_correct:
                get_vocab_manager().remove_word_from_wrong_book(w['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(w['word'], w.get('part_of_speech', ''), w['meaning'])
        except Exception:
            pass
    
    es['pattern_score'] = strategy_score
    es['pattern_results'] = results
    es['pattern_words_data'] = [
    {
        'word': r['word'],
        'part_of_speech': r.get('pos', ''),
        'meaning': r['meaning'],
        'is_correct': r['is_correct'],
        'score': r.get('score', '1.00' if r['is_correct'] else '0.00')
    }
    for r in results
]
    
    basic_score = es.get('basic_score', 0)
    total_score = basic_score + strategy_score
    is_passed = total_score >= PATTERN_PASS_SCORES.get('七十二变', 47)
    print(f"!!! 72_submit: selected_pattern={es.get('selected_pattern')}")
    
    
    save_final_record(es, strategy_score)
    
    return jsonify({'success': True, 'results': results, 'strategy_score': strategy_score, 'basic_score': basic_score, 'total_score': total_score, 'is_passed': is_passed})

# ========== 三十六计20分 API ==========
@shadow_hunter_bp.route('/api/shadow_hunter/thirtysix_start', methods=['POST'])
def thirtysix_start():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})

    prep = es.get('pattern_prep') or {}
    if prep.get('ready') and prep.get('data'):
        strategy_data = prep['data']
        error = None
    elif es.get('meanings_36') and es.get('card_pool_36'):
        strategy_data = {
            'meanings': es['meanings_36'],
            'card_pool': es['card_pool_36'],
        }
        error = None
    else:
        strategy_data, error = None, '出题失败'
        for _ in range(5):
            strategy_data, error = prepare_strategy_words_36_full(es['today'], es['yesterday'])
            if not error:
                break
    if error:
        return jsonify({'success': False, 'message': f'出题失败: {error}'})

    es['meanings_36'] = strategy_data['meanings']
    es['card_pool_36'] = strategy_data['card_pool']
    es['hand_cards_36'] = strategy_data['card_pool'][:7]
    es['pool_index_36'] = 7
    es['placements_36'] = {}

    return jsonify({
        'success': True,
        'meanings': [{'meaning': m['meaning'], 'index': i} for i, m in enumerate(es['meanings_36'])],
        'hand_cards': es['hand_cards_36'],
        'placements': es['placements_36'],
        'pool_remaining': len(es['card_pool_36']) - es['pool_index_36'],
    })

@shadow_hunter_bp.route('/api/shadow_hunter/thirtysix_place', methods=['POST'])
def thirtysix_place():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    card_id = data.get('card_id', '')
    meaning_index = data.get('meaning_index', -1)
    if sum(1 for v in es['placements_36'].values() if v == meaning_index) >= 3: return jsonify({'success': False, 'message': '该区域已满'})
    
    es['placements_36'][card_id] = meaning_index
    es['hand_cards_36'] = [c for c in es['hand_cards_36'] if c['id'] != card_id]
    if es['pool_index_36'] < len(es['card_pool_36']):
        es['hand_cards_36'].append(es['card_pool_36'][es['pool_index_36']])
        es['pool_index_36'] += 1
    return jsonify({'success': True, 'hand_cards': es['hand_cards_36'], 'placements': es['placements_36']})

@shadow_hunter_bp.route('/api/shadow_hunter/thirtysix_submit', methods=['POST'])
def thirtysix_submit():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    area_correct = {}
    for card_id, mi in es['placements_36'].items():
        card_data = next((c for c in es['card_pool_36'] if c['id'] == card_id), None)
        if card_data and card_data['meaning_index'] == mi: area_correct[mi] = area_correct.get(mi, 0) + 1
    
    strategy_score = 0
    for mi in range(10):
        matches = area_correct.get(mi, 0)
        if matches >= 2:
            strategy_score += 2
        elif matches == 1:
            strategy_score += 1

    results = []
    for card in es['card_pool_36']:
        card_id = card['id']
        placed_mi = es['placements_36'].get(card_id)
        is_correct = (placed_mi is not None and placed_mi == card['meaning_index'])
        results.append({
            'word': card['word'], 'pos': card['pos'], 'meaning': card['meaning'],
            'target_meaning': card['target_meaning'], 'is_correct': is_correct,
            'score': '1.00' if is_correct else '0.00',
        })
        try:
            if is_correct:
                get_vocab_manager().remove_word_from_wrong_book(card['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(card['word'], card['pos'], card['meaning'])
        except Exception:
            pass
    
    es['pattern_score'] = strategy_score
    es['pattern_results'] = results
    es['pattern_words_data'] = [
    {
        'word': r['word'],
        'part_of_speech': r.get('pos', ''),
        'meaning': r.get('meaning', r.get('meaning', '')),
        'is_correct': r['is_correct'],
        'score': r.get('score', '1.00' if r['is_correct'] else '0.00')
    }
    for r in results
]
    es['area_correct_36'] = area_correct
    
    basic_score = es.get('basic_score', 0)
    total_score = basic_score + strategy_score
    is_passed = total_score >= PATTERN_PASS_SCORES.get('三十六计', 47)
    
    save_final_record(es, strategy_score)
    
    return jsonify({
        'success': True,
        'results': results,
        'strategy_score': strategy_score,
        'basic_score': basic_score,
        'total_score': total_score,
        'is_passed': is_passed,
        'area_correct': area_correct,
        'meanings': [{'meaning': m['meaning']} for m in es['meanings_36']],
    })

# ========== 盗宝大师20分 API ==========
ALL_SKILLS = ['重置', '翻牌', '预言', '孤注一掷', '看破', '科技之星', '枫恬果实']
SKILL_INFO = {'重置': {'max': 3}, '翻牌': {'max': 1}, '预言': {'max': 1}, '孤注一掷': {'max': 1}, '看破': {'max': 2}, '科技之星': {'max': 1}, '枫恬果实': {'max': 1}}

@shadow_hunter_bp.route('/api/shadow_hunter/treasure_start', methods=['POST'])
def treasure_start():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    selected_skills = data.get('selected_skills', [])
    if len(selected_skills) != 2: return jsonify({'success': False, 'message': '请选择2个技能'})
    
    error = _ensure_treasure_data(es)
    if error:
        return jsonify({'success': False, 'message': error})
    
    es['user_choices_tr'] = {}
    es['treasure_score'] = 0
    es['current_round_tr'] = 0
    es['selected_skills_tr'] = selected_skills
    es['skill_remaining_tr'] = {s: SKILL_INFO[s]['max'] for s in selected_skills}
    es['found_true_treasure'] = False
    
    return jsonify({'success': True, 'selected_skills': selected_skills, 'skill_remaining': es['skill_remaining_tr']})

@shadow_hunter_bp.route('/api/shadow_hunter/treasure_round', methods=['POST'])
def treasure_round():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    ri = es['current_round_tr']
    if ri >= 20: return jsonify({'success': False, 'game_over': True})
    w = es['treasure_words'][ri]
    empty_seq = [5, 1, 2, 3, 4]
    ec = empty_seq[ri % 5]
    return jsonify({'success': True, 'round': ri+1, 'total_rounds': 20, 'word': w['word'], 'pos': w['pos'], 'empty_card': ec, 'meanings': es['treasure_meanings'][ri], 'current_score': es['treasure_score'], 'skill_remaining': es['skill_remaining_tr']})

@shadow_hunter_bp.route('/api/shadow_hunter/treasure_choice', methods=['POST'])
def treasure_choice():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    ri = es['current_round_tr']
    
    if data.get('use_reset') and es['skill_remaining_tr'].get('重置', 0) > 0:
        es['skill_remaining_tr']['重置'] -= 1
        correct_card = es['treasure_answers'][ri]
        empty_seq = [5, 1, 2, 3, 4]
        nec = empty_seq[ri % 5]
        available_words = []
        current_word = es['treasure_words'][ri]['word']
        for g in get_vocab_manager().get_all_groups():
            if g['group_name'] in [es['today'], es['yesterday']]: continue
            gdata = get_vocab_manager().get_word_group(g['group_name'], g.get('dict_name', ''))
            if gdata and 'words' in gdata:
                for w in gdata['words']:
                    if w['word'] != current_word: available_words.append(w)
        if available_words:
            nw = random.choice(available_words)
            es['treasure_words'][ri] = {'word': nw['word'], 'pos': nw.get('part_of_speech',''), 'meaning': nw.get('chinese_meaning','')}
            ncm = nw.get('chinese_meaning','')
            npos = nw.get('part_of_speech','')
            es['treasure_meanings'][ri][str(correct_card)] = ncm
            nwp = generate_wrong_meanings_for_web(ncm, npos, nw['word'], set(), es.get('_words_pool'))
            noc = [c for c in range(1, 6) if c != correct_card and c != nec]
            for j, card in enumerate(noc): es['treasure_meanings'][ri][str(card)] = nwp[j] if j < len(nwp) else f'错{j+1}'
        return jsonify({'success': True, 'current_score': es['treasure_score'], 'reset_done': True, 'skill_remaining': es['skill_remaining_tr']})
    
    choice = data.get('choice', 0)
    correct_card = es['treasure_answers'][ri]
    if choice == correct_card: es['treasure_score'] += 1
    es['user_choices_tr'][str(ri)] = choice
    es['current_round_tr'] += 1
    return jsonify({'success': True, 'current_score': es['treasure_score'], 'next_round': es['current_round_tr']+1 if es['current_round_tr'] < 20 else None, 'skill_remaining': es['skill_remaining_tr']})

@shadow_hunter_bp.route('/api/shadow_hunter/treasure_skill', methods=['POST'])
def treasure_skill():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    skill = data.get('skill', '')
    if skill not in es['skill_remaining_tr'] or es['skill_remaining_tr'][skill] <= 0: return jsonify({'success': False, 'message': '技能不可用'})
    result = {}
    if skill == '翻牌':
        t = data.get('target', 1)
        cnt = sum(1 for i in range(20) if es['treasure_answers'][i] == t)
        es['skill_remaining_tr'][skill] -= 1
        result = {'treasure': t, 'count': cnt}
    elif skill == '预言':
        cnt = sum(1 for i in range(20) if es['treasure_answers'][i] == es['true_treasure'])
        es['skill_remaining_tr'][skill] -= 1
        result = {'count': cnt}
    elif skill == '看破':
        ri = data.get('round_idx', 0)
        ok = (es['user_choices_tr'].get(str(ri)) == es['treasure_answers'][ri])
        es['skill_remaining_tr'][skill] -= 1
        result = {'round': ri+1, 'is_correct': ok}
    elif skill == '科技之星':
        rounds = data.get('rounds', [])
        c = sum(1 for r in rounds if es['user_choices_tr'].get(str(r)) == es['treasure_answers'][r])
        es['skill_remaining_tr'][skill] -= 1
        result = {'correct': c, 'status': 'green' if c==4 else ('yellow' if c==3 else 'red')}
    elif skill == '枫恬果实':
        ri = data.get('round_idx', 0)
        is_correct = (es['user_choices_tr'].get(str(ri)) == es['treasure_answers'][ri])
        es['skill_remaining_tr'][skill] -= 1
        if is_correct: es['treasure_score'] = min(es['treasure_score'] + 1, 20)
        result = {'is_correct': is_correct, 'correct_card': es['treasure_answers'][ri], 'round': ri+1}
    elif skill in ['孤注一掷', '重置']: result = {'available': True}
    return jsonify({'success': True, 'result': result, 'skill_remaining': es['skill_remaining_tr']})
@shadow_hunter_bp.route('/api/shadow_hunter/treasure_final', methods=['POST'])
def treasure_final():
    """盗宝大师获取最终报告（20轮详情+宝藏卡统计）"""
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    total = es.get('basic_score', 0) + es['treasure_score']
    ts = {1:0,2:0,3:0,4:0,5:0}
    for c in es['user_choices_tr'].values():
        if c in ts: ts[c] += 1
    
    rounds_detail = []
    for i in range(20):
        w = es['treasure_words'][i]
        uc = es['user_choices_tr'].get(str(i), 0)
        is_correct = (uc == es['treasure_answers'][i])
        rounds_detail.append({
            'round': i+1, 'word': w['word'], 'pos': w['pos'],
            'meaning': w['meaning'], 'correct_card': es['treasure_answers'][i],
            'user_choice': uc, 'is_correct': is_correct
        })
        try:
            if is_correct:
                get_vocab_manager().remove_word_from_wrong_book(w['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(w['word'], w['pos'], w['meaning'])
        except Exception:
            pass
    
    return jsonify({
        'success': True,
        'basic_score': es.get('basic_score', 0),
        'treasure_score': es['treasure_score'],
        'total_score': total,
        'true_treasure': es['true_treasure'],
        'treasure_counts': es['treasure_counts'],
        'treasure_selects': ts,
        'found_true_treasure': es.get('found_true_treasure', False),
        'final_selected': es.get('final_treasure_selected'),
        'rounds_detail': rounds_detail,
        'today_group': es['today'],
        'selected_skills': es['selected_skills_tr'],
        'skill_remaining': es['skill_remaining_tr']
    })











@shadow_hunter_bp.route('/api/shadow_hunter/treasure_dig', methods=['POST'])
def treasure_dig():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    selected = data.get('treasure', 1)
    is_correct = (selected == es['true_treasure'])
    gambled = False
    final_selected = selected
    final_is_correct = is_correct
    if not is_correct and es['skill_remaining_tr'].get('孤注一掷', 0) > 0:
        es['skill_remaining_tr']['孤注一掷'] -= 1
        gambled = True
        final_selected = es['true_treasure'] if random.random() < 0.25 else random.choice([c for c in range(1, 6) if c != es['true_treasure']])
        final_is_correct = (final_selected == es['true_treasure'])
    
    es['found_true_treasure'] = final_is_correct
    es['final_treasure_selected'] = final_selected
    es['pattern_score'] = es['treasure_score']

    es['pattern_words_data'] = [
    {
        'word': w['word'],
        'part_of_speech': w.get('pos', ''),
        'meaning': w.get('meaning', ''),
        'is_correct': es['user_choices_tr'].get(str(i), 0) == es['treasure_answers'][i]
    }
    for i, w in enumerate(es['treasure_words'])
]
    
    basic_score = es.get('basic_score', 0)
    total_score = basic_score + es['treasure_score']
    is_passed = total_score >= PATTERN_PASS_SCORES.get('盗宝大师', 46) and final_is_correct
    
    save_final_record(es, es['treasure_score'], found_true_treasure=final_is_correct)
    
    return jsonify({'success': True, 'is_correct': final_is_correct, 'true_treasure': es['true_treasure'], 'selected': final_selected, 'gambled': gambled, 'total_score': total_score, 'is_passed': is_passed, 'treasure_score': es['treasure_score'], 'basic_score': basic_score})

# ========== 通用：保存记录 + 获取最终报告 ==========
def save_final_record(es, pattern_score, found_true_treasure=False):
    print(f"!!! SAVE: selected_pattern={es.get('selected_pattern')}, today={es.get('today')}")
   
    try:
        basic_score = es.get('basic_score', 0)
        total_score = basic_score + pattern_score
        selected_pattern = es.get('selected_pattern', '')
        pass_score = PATTERN_PASS_SCORES.get(selected_pattern, 46)
        
        if selected_pattern == '盗宝大师':
            is_passed = total_score >= pass_score and es.get('found_true_treasure', False)
        else:
            is_passed = total_score >= pass_score
        
        # 构建版型数据
        pattern_data = {'type': selected_pattern, 'final_score': pattern_score}
        pattern_words = es.get('pattern_words_data', [])
        if selected_pattern == '诡影重重':
            pattern_data['shadow_words'] = pattern_words
        elif selected_pattern == '七十二变':
            pattern_data['word_cards'] = pattern_words
        elif selected_pattern == '三十六计':
            pattern_data['all_words'] = pattern_words
        elif selected_pattern == '盗宝大师':
            pattern_data['treasure_words'] = pattern_words
        
        exam_data = {
            'basic_words': [],
            'pattern_data': pattern_data,
            'pattern_name': selected_pattern,
            'drawn_pattern': selected_pattern,
            'pass_score': pass_score,
            'exam_type': '阴影迷踪',
        }
        
        # 基础词汇数据
        for r in es.get('basic_results', []):
            exam_data['basic_words'].append({
                'word': r.get('word', ''),
                'part_of_speech': r.get('pos', ''),
                'meaning': r.get('meaning', ''),
                'user_answer': r.get('user_answer', ''),
                'score': r.get('score', 0.0)
            })
        
        record_details = json.dumps(exam_data, ensure_ascii=False)
        
        get_stats_db().update_or_create_stats(
            group_name=es['today'],
            dictionary_name=es['dictionary_name'],
            score=total_score,
            passed=is_passed,
            pattern_name=selected_pattern,
            pass_score_override=pass_score,
        )
        get_stats_db().add_exam_record(
            group_name=es['today'],
            dictionary_name=es['dictionary_name'],
            pattern_name=selected_pattern,
            score=total_score,
            is_passed=is_passed,
            basic_score=basic_score,
            shadow_score=pattern_score,
            total_score=total_score,
            record_details=record_details,
            pass_score_override=pass_score,
        )
        print(f"✓ 阴影迷踪记录已保存: {es['today']} - 抽取{selected_pattern} - 计入{selected_pattern}积分 - {total_score:.2f}分")
    except Exception as e:
        print(f"保存记录失败: {e}")
        import traceback
        traceback.print_exc()

@shadow_hunter_bp.route('/api/shadow_hunter/final_report', methods=['POST'])
def final_report():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    return jsonify({'success': True, 'basic_results': es.get('basic_results', []), 'basic_score': es.get('basic_score', 0), 'pattern_score': es.get('pattern_score', 0), 'pattern_results': es.get('pattern_results', []), 'selected_pattern': es.get('selected_pattern', ''), 'today': es.get('today', ''), 'total_score': es.get('basic_score', 0) + es.get('pattern_score', 0)})

# ========== 辅助函数（从各版型复制过来） ==========
def process_wrong_books_shadow(results):
    for r in results:
        try:
            if r['score'] >= 1.0: get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else: get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except: pass