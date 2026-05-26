# shadow_hunter_web.py - 阴影迷踪网页版（完整版）
from flask import Blueprint, render_template, request, jsonify
from exam_base_web import prepare_basic_words, get_all_group_names, calculate_similarity
from vocabulary_manager import VocabularyManager
from exam_stats_db import ExamStatsDB
import random, os, uuid, json, sqlite3, re, difflib, math
from ai_correct import ai_corrector
from settings_web import get_all_settings
shadow_hunter_bp = Blueprint('shadow_hunter', __name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocabulary.db")
vm = VocabularyManager(db_path=DB_PATH)
stats_db = ExamStatsDB("exam_stats.db", "vocabulary.db")

PATTERN_PASS_SCORES = {"盗宝大师": 46, "诡影重重": 45, "三十六计": 47, "七十二变": 47}
FULL_SCORE = 50
BASIC_FULL = 30
PATTERNS = ["七十二变", "三十六计", "盗宝大师", "诡影重重"]
PATTERN_WEIGHTS = [0, 0, 1, 0]
TREASURE_NAMES = ['青山', '寒山', '沧山', '暮山', '尘山']

exam_sessions = {}

@shadow_hunter_bp.route('/exam/shadow_hunter')
def shadow_hunter_page():
    return render_template('shadow_hunter.html',
                         groups=get_all_group_names(),
                         patterns=PATTERNS,
                         pattern_pass_scores=PATTERN_PASS_SCORES,
                         full_score=FULL_SCORE,
                         basic_full=BASIC_FULL)


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
        conn = sqlite3.connect(DB_PATH)
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
    
    exam_sessions[exam_id] = {
        'basic': [{'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning']} for w in basic_words],
        'today': today,
        'yesterday': yesterday,
        'dictionary_name': dictionary_name,
        'basic_results': [],
        'basic_score': 0,
        'selected_pattern': None
    }
    
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
                vm.remove_word_from_wrong_book(r['word'])
            else:
                vm.add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass
    
    return jsonify({
        'success': True,
        'results': results,
        'score': round(total_score, 2),
        'total': len(words),
        'used_ai': used_ai
    })


@shadow_hunter_bp.route('/api/shadow_hunter/draw_pattern', methods=['POST'])
def draw_pattern():
    """抽取版型"""
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    
    selected = random.choices(PATTERNS, weights=PATTERN_WEIGHTS, k=1)[0]
    es['selected_pattern'] = selected
    
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
        
# ========== 诡影重重20分 API ==========
@shadow_hunter_bp.route('/api/shadow_hunter/shadow_start', methods=['POST'])
def shadow_start():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    shadow_words, error = prepare_shadow_words(es['today'], es['yesterday'])
    if error: return jsonify({'success': False, 'message': error})
    
    es['shadow_words'] = [{'word': w['word'], 'pos': w['part_of_speech'], 'meaning': w['chinese_meaning']} for w in shadow_words]
    return jsonify({'success': True, 'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(es['shadow_words'])], 'total': len(es['shadow_words'])})

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
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    suffix_words, similar_words, error = prepare_strategy_words_72(es['today'], es['yesterday'])
    if error: return jsonify({'success': False, 'message': error})
    
    suffix_meanings = build_meaning_options_72(suffix_words)
    similar_meanings = build_meaning_options_72(similar_words)
    
    es['suffix_words'] = suffix_words
    es['similar_words'] = similar_words
    es['suffix_meanings'] = suffix_meanings
    es['similar_meanings'] = similar_meanings
    
    return jsonify({'success': True, 'suffix_words': suffix_words, 'similar_words': similar_words, 'suffix_meanings': suffix_meanings, 'similar_meanings': similar_meanings})

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
        if is_correct: strategy_score += 1
        results.append({'id': w['id'], 'word': w['word'], 'pos': w.get('part_of_speech',''), 'meaning': w['meaning'], 'user_meaning': user_meaning, 'is_correct': is_correct, 'score': '1.00' if is_correct else '0.00'})
    
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
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    
    strategy_data, error = prepare_strategy_words_36(es['today'], es['yesterday'])
    if error: return jsonify({'success': False, 'message': error})
    
    es['meanings_36'] = strategy_data['meanings']
    es['card_pool_36'] = strategy_data['card_pool']
    es['hand_cards_36'] = strategy_data['card_pool'][:7]
    es['pool_index_36'] = 7
    es['placements_36'] = {}
    
    return jsonify({'success': True, 'meanings': [{'meaning': m['meaning'], 'index': i} for i, m in enumerate(es['meanings_36'])], 'hand_cards': es['hand_cards_36'], 'placements': es['placements_36'], 'pool_remaining': len(es['card_pool_36']) - es['pool_index_36']})

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
    
    strategy_score = sum(2 if area_correct.get(mi, 0) >= 2 else (1 if area_correct.get(mi, 0) == 1 else 0) for mi in range(10))
    
    results = []
    for card_id, mi in es['placements_36'].items():
        card_data = next((c for c in es['card_pool_36'] if c['id'] == card_id), None)
        if not card_data: continue
        is_correct = (card_data['meaning_index'] == mi)
        results.append({'word': card_data['word'], 'pos': card_data['pos'], 'meaning': card_data['meaning'], 'target_meaning': card_data['target_meaning'], 'is_correct': is_correct, 'score': '1.00' if is_correct else '0.00'})
    
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
    
    return jsonify({'success': True, 'results': results, 'strategy_score': strategy_score, 'basic_score': basic_score, 'total_score': total_score, 'is_passed': is_passed, 'area_correct': area_correct})

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
    
    treasure_words, error = prepare_treasure_words(es['today'], es['yesterday'])
    if error: return jsonify({'success': False, 'message': error})
    
    answers, meanings, true_treasure, treasure_counts = generate_treasure_answers(treasure_words)
    
    es['treasure_words'] = [{'word': w['word'], 'pos': w.get('part_of_speech',''), 'meaning': w.get('chinese_meaning','')} for w in treasure_words]
    es['treasure_answers'] = answers
    es['treasure_meanings'] = meanings
    es['true_treasure'] = true_treasure
    es['treasure_counts'] = treasure_counts
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
        for g in vm.get_all_groups():
            if g['group_name'] in [es['today'], es['yesterday']]: continue
            gdata = vm.get_word_group(g['group_name'], g.get('dict_name', ''))
            if gdata and 'words' in gdata:
                for w in gdata['words']:
                    if w['word'] != current_word: available_words.append(w)
        if available_words:
            nw = random.choice(available_words)
            es['treasure_words'][ri] = {'word': nw['word'], 'pos': nw.get('part_of_speech',''), 'meaning': nw.get('chinese_meaning','')}
            ncm = nw.get('chinese_meaning','')
            npos = nw.get('part_of_speech','')
            es['treasure_meanings'][ri][str(correct_card)] = ncm
            nwp = generate_wrong_meanings_for_web(ncm, npos, nw['word'], set())
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
            'pattern_name': selected_pattern
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
        
        stats_db.update_or_create_stats(
            group_name=es['today'],
            dictionary_name=es['dictionary_name'],
            score=total_score,
            passed=is_passed,
            pattern_name=selected_pattern
        )
        stats_db.add_exam_record(
            group_name=es['today'],
            dictionary_name=es['dictionary_name'],
            pattern_name=selected_pattern,
            score=total_score,
            is_passed=is_passed,
            basic_score=basic_score,
            shadow_score=pattern_score,
            total_score=total_score,
            record_details=record_details
        )
        print(f"✓ 记录已保存: {es['today']} - {selected_pattern} - {total_score:.2f}分")
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
def prepare_shadow_words(today, yesterday):
    # 同 shadow_exam_web.py 中的 prepare_shadow_words
    all_groups = vm.get_all_groups()
    other_words = []
    for g in all_groups:
        if g['group_name'] in [today, yesterday]: continue
        gdata = vm.get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            words = gdata['words']; n = min(5, len(words))
            for w in random.sample(words, n): other_words.append({'word': w['word'], 'part_of_speech': w.get('part_of_speech',''), 'chinese_meaning': w.get('chinese_meaning','')})
            if len(other_words) >= 100: break
    if len(other_words) < 30: return None, '候选单词不足'
    def clean_meaning(m): return re.sub(r'[的地了是]', '', m)
    filtered, char_sets = [], []
    for w in other_words:
        cm = clean_meaning(w['chinese_meaning']); filtered.append(w); char_sets.append(set(re.findall(r'[\u4e00-\u9fff]', cm)))
    to_remove = set()
    for i in range(len(filtered)):
        if i in to_remove: continue
        for j in range(i+1, len(filtered)):
            if j in to_remove: continue
            if len(char_sets[i] & char_sets[j]) >= 2: to_remove.add(random.choice([i, j]))
    final = [w for idx, w in enumerate(filtered) if idx not in to_remove]
    if len(final) < 30: return None, '过滤后单词不足'
    return random.sample(final, 30), None

def calc_shadow_score(ua, ca):
    if not ua: return 0.0
    sim = calculate_similarity(ua, ca)
    return 1.0 if sim >= 2 else (0.75 if sim == 1 else 0.0)

def process_wrong_books_shadow(results):
    for r in results:
        try:
            if r['score'] >= 1.0: vm.remove_word_from_wrong_book(r['word'])
            else: vm.add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except: pass

def prepare_strategy_words_72(today, yesterday):
    # 同 seventy_two_web.py
    all_words = []
    for g in vm.get_all_groups():
        gdata = vm.get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            for w in gdata['words']: all_words.append({'word': w['word'], 'chinese_meaning': w.get('chinese_meaning',''), 'part_of_speech': w.get('part_of_speech','')})
    if len(all_words) < 30: return None, None, '词汇不足'
    affixes = ['-tion','-sion','-ment','-ness','-ity','-ance','-ence','-er','-or','-ist','-ism','-able','-ible','-ive','-ous','-ful','-less','-al','-ic','-ly','un-','re-','pre-','dis-','mis-','over-','under-','inter-','trans-','sub-']
    random.shuffle(affixes)
    suffix_words = None
    for affix in affixes:
        candidates = []
        for w in all_words:
            word = w['word'].lower()
            if affix.startswith('-') and word.endswith(affix[1:]): candidates.append({'word': w['word'], 'meaning': w['chinese_meaning'], 'part_of_speech': w.get('part_of_speech','')})
            elif affix.endswith('-') and word.startswith(affix[:-1]): candidates.append({'word': w['word'], 'meaning': w['chinese_meaning'], 'part_of_speech': w.get('part_of_speech','')})
        if len(candidates) >= 10:
            filtered = [candidates[0]]
            for c in candidates[1:]:
                ok = True
                for f in filtered:
                    if difflib.SequenceMatcher(None, c['meaning'], f['meaning']).ratio() >= 0.4: ok = False; break
                if ok: filtered.append(c)
                if len(filtered) >= 10: break
            if len(filtered) >= 10:
                suffix_words = random.sample(filtered, 10)
                for i, sw in enumerate(suffix_words): sw['id'] = f'suffix_{i}'
                break
    if not suffix_words: return None, None, '同缀词不足'
    similar_pairs = []
    check_count = min(len(all_words), 500)
    for i in range(check_count):
        for j in range(i+1, check_count):
            w1, w2 = all_words[i], all_words[j]
            if w1['word'].lower() == w2['word'].lower(): continue
            ws = difflib.SequenceMatcher(None, w1['word'].lower(), w2['word'].lower()).ratio()
            if ws >= 0.74:
                ms = difflib.SequenceMatcher(None, w1['chinese_meaning'], w2['chinese_meaning']).ratio()
                if ms <= 0.4: similar_pairs.append((w1, w2))
    if len(similar_pairs) < 5: return suffix_words, None, '相似词对不足'
    random.shuffle(similar_pairs)
    similar_words, used = [], set()
    for w1, w2 in similar_pairs:
        if w1['word'] in used or w2['word'] in used: continue
        used.add(w1['word']); used.add(w2['word'])
        pid = len(similar_words)//2
        similar_words.append({'id': f'similar_{pid}_1', 'word': w1['word'], 'meaning': w1['chinese_meaning'], 'part_of_speech': w1.get('part_of_speech',''), 'pair_id': pid})
        similar_words.append({'id': f'similar_{pid}_2', 'word': w2['word'], 'meaning': w2['chinese_meaning'], 'part_of_speech': w2.get('part_of_speech',''), 'pair_id': pid})
        if len(similar_words) >= 10: break
    return suffix_words, similar_words, None

def build_meaning_options_72(words_list):
    correct_meanings = [w['meaning'] for w in words_list]
    all_meanings = correct_meanings.copy()
    all_vocab = []
    for g in vm.get_all_groups():
        gdata = vm.get_word_group(g['group_name'], g.get('dict_name',''))
        if gdata and 'words' in gdata:
            for w in gdata['words']: all_vocab.append(w.get('chinese_meaning',''))
    random.shuffle(all_vocab)
    for m in all_vocab:
        if m not in all_meanings: all_meanings.append(m)
        if len(all_meanings) >= len(correct_meanings)+2: break
    random.shuffle(all_meanings)
    return [{'text': m, 'is_correct': m in correct_meanings} for m in all_meanings]

def split_meanings_36(meaning_str): return [m.strip() for m in meaning_str.split(';') if m.strip()]
def split_into_words_36(text):
    if ';' in text: return [w.strip() for w in text.split(';') if w.strip()]
    words = []; current = ''
    for char in text:
        if char not in [' ', '，', '；', ',', ';']: current += char
        elif current: words.append(current); current = ''
    if current: words.append(current)
    return words if words else [text]
def calc_single_meaning_similarity(m1, m2):
    if not m1 or not m2: return 0.0
    if m1 == m2: return 1.0
    if m1 in m2 or m2 in m1: return 0.9
    w1 = split_into_words_36(m1); w2 = split_into_words_36(m2)
    common = set(w1) & set(w2)
    if common: return 0.8 + len(common) * 0.1
    s1, s2 = set(m1), set(m2)
    if not s1 or not s2: return 0.0
    return len(s1 & s2) / len(s1 | s2)
def check_pos_match_36(pos1, pos2):
    p1 = [p.strip() for p in pos1.split('/') if p.strip()]; p2 = [p.strip() for p in pos2.split('/') if p.strip()]
    return bool(set(p1) & set(p2)) if p1 and p2 else True

def prepare_strategy_words_36(today, yesterday):
    all_words = []; seen = set()
    for g in vm.get_all_groups():
        gdata = vm.get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            for w in gdata['words']:
                key = (w['word'].lower(), w.get('chinese_meaning', ''))
                if key not in seen: seen.add(key); all_words.append(w)
    if len(all_words) < 100: return None, '词汇不足'
    basic_words, _ = prepare_basic_words(today, yesterday)
    if not basic_words: return None, '基础词汇不足'
    meanings, used_words, used_meanings, used_base_words = [], set(), set(), set()
    check_count = int(len(all_words) * 0.75)
    for _ in range(1000):
        if len(meanings) >= 10: break
        bw = random.choice(basic_words); bw_key = bw['word'].lower()
        if bw_key in used_base_words: continue
        bw_pos = bw.get('pos', bw.get('part_of_speech', '')); bw_pos_list = [p.strip() for p in bw_pos.split('/') if p.strip()]
        if not bw_pos_list: continue
        bw_meanings = split_meanings_36(bw.get('meaning', bw.get('chinese_meaning', '')))
        if not bw_meanings: continue
        selected_meaning = random.choice(bw_meanings)
        if selected_meaning in used_meanings: continue
        if any(calc_single_meaning_similarity(selected_meaning, e['meaning']) >= 0.4 for e in meanings): continue
        random_check = random.sample(all_words, min(check_count, len(all_words)))
        similar_words = []
        for dw in random_check:
            if not check_pos_match_36(bw_pos, dw.get('part_of_speech', '')): continue
            if dw['word'].lower() in used_words: continue
            if any(calc_single_meaning_similarity(selected_meaning, dm) >= 0.8 for dm in split_meanings_36(dw.get('chinese_meaning', ''))): similar_words.append({'word': dw['word'], 'part_of_speech': dw.get('part_of_speech',''), 'chinese_meaning': dw.get('chinese_meaning',''), 'is_itself': dw['word'].lower() == bw_key})
        if not any(w['is_itself'] for w in similar_words) and bw_key not in used_words: similar_words.append({'word': bw['word'], 'part_of_speech': bw_pos, 'chinese_meaning': bw.get('meaning', bw.get('chinese_meaning','')), 'is_itself': True})
        if len(similar_words) >= 3:
            selected, selected_keys = [], set()
            self_word = next((w for w in similar_words if w['is_itself']), None)
            if self_word and self_word['word'].lower() not in used_words: selected.append(self_word); selected_keys.add(self_word['word'].lower())
            for w in similar_words:
                if not w['is_itself'] and len(selected) < 3 and w['word'].lower() not in used_words and w['word'].lower() not in selected_keys: selected.append(w); selected_keys.add(w['word'].lower())
            if len(selected) == 3:
                for sw in selected: used_words.add(sw['word'].lower())
                meanings.append({'meaning': selected_meaning, 'words': selected, 'from_basic': True}); used_meanings.add(selected_meaning); used_base_words.add(bw_key)
    if len(meanings) < 10:
        available = [w for w in all_words if w['word'].lower() not in used_words]
        for _ in range(1000):
            if len(meanings) >= 10 or not available: break
            dw = random.choice(available); dw_key = dw['word'].lower()
            dw_pos = dw.get('part_of_speech', ''); dw_pos_list = [p.strip() for p in dw_pos.split('/') if p.strip()]
            if not dw_pos_list: continue
            dw_meanings = split_meanings_36(dw.get('chinese_meaning', ''))
            if not dw_meanings: continue
            selected_meaning = random.choice(dw_meanings)
            if selected_meaning in used_meanings: continue
            if any(calc_single_meaning_similarity(selected_meaning, e['meaning']) >= 0.4 for e in meanings): continue
            similar_words = []
            for cw in random.sample(all_words, min(check_count, len(all_words))):
                if not check_pos_match_36(dw_pos, cw.get('part_of_speech', '')): continue
                if cw['word'].lower() in used_words: continue
                if any(calc_single_meaning_similarity(selected_meaning, cm) >= 0.8 for cm in split_meanings_36(cw.get('chinese_meaning', ''))): similar_words.append({'word': cw['word'], 'part_of_speech': cw.get('part_of_speech',''), 'chinese_meaning': cw.get('chinese_meaning',''), 'is_itself': cw['word'].lower() == dw_key})
            if not any(w['is_itself'] for w in similar_words) and dw_key not in used_words: similar_words.append({'word': dw['word'], 'part_of_speech': dw_pos, 'chinese_meaning': dw.get('chinese_meaning',''), 'is_itself': True})
            if len(similar_words) >= 3:
                selected, selected_keys = [], set()
                self_word = next((w for w in similar_words if w['is_itself']), None)
                if self_word and self_word['word'].lower() not in used_words: selected.append(self_word); selected_keys.add(self_word['word'].lower())
                for w in similar_words:
                    if not w['is_itself'] and len(selected) < 3 and w['word'].lower() not in used_words and w['word'].lower() not in selected_keys: selected.append(w); selected_keys.add(w['word'].lower())
                if len(selected) == 3:
                    for sw in selected: used_words.add(sw['word'].lower())
                    meanings.append({'meaning': selected_meaning, 'words': selected, 'from_basic': False}); used_meanings.add(selected_meaning)
    if len(meanings) < 10: return None, f'只找到{len(meanings)}个汉译'
    card_pool = []
    for mi, m in enumerate(meanings):
        for wi, w in enumerate(m['words']): card_pool.append({'id': f'card_{mi}_{wi}', 'word': w['word'], 'pos': w.get('part_of_speech',''), 'meaning': w.get('chinese_meaning',''), 'target_meaning': m['meaning'], 'meaning_index': mi})
    if any(sum(1 for c in card_pool if c['word'].lower() == k) > 1 for k in set(c['word'].lower() for c in card_pool)): return None, '出题出现重复单词'
    return {'meanings': meanings, 'card_pool': card_pool}, None

def prepare_treasure_words(today, yesterday):
    all_words, seen = [], set()
    for g in vm.get_all_groups():
        if g['group_name'] in [today, yesterday]: continue
        gdata = vm.get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            for w in gdata['words']:
                key = (w['word'].lower(), w.get('chinese_meaning', ''))
                if key not in seen: seen.add(key); all_words.append(w)
    if len(all_words) < 20: return None, '词汇不足'
    return random.sample(all_words, 20), None

def calculate_word_similarity(w1, w2):
    if not w1 or not w2: return 0
    s1, s2 = set(w1.lower()), set(w2.lower())
    return len(s1 & s2) / len(s1 | s2) if s1 | s2 else 0

def has_too_many_common_chars(t1, t2):
    if not t1 or not t2: return False
    fc = ['的','地','得','了','在','是','有','和','与','及','或','使','让','把','被','不','错误']
    def ft(t): return ''.join([c for c in t if c not in fc])
    a, b = ft(t1), ft(t2)
    return len(set(a) & set(b)) >= 2 if a and b else False

def generate_wrong_meanings_for_web(correct_meaning, correct_pos, current_word, used_wrong_meanings):
    all_groups = vm.get_all_groups()
    candidate_meanings, used_meanings = [], set()
    shuffled_groups = all_groups.copy(); random.shuffle(shuffled_groups)
    for group in shuffled_groups:
        gdata = vm.get_word_group(group['group_name'], group.get('dict_name', ''))
        if gdata and 'words' in gdata:
            for word in random.sample(gdata['words'], len(gdata['words'])):
                if word.get('part_of_speech','') != correct_pos: continue
                if word['word'].lower() == current_word.lower(): continue
                if calculate_word_similarity(current_word.lower(), word['word'].lower()) < 0.7: continue
                cm = word.get('chinese_meaning','')
                if cm == correct_meaning or cm in used_meanings or cm in used_wrong_meanings: continue
                if has_too_many_common_chars(cm, correct_meaning): continue
                candidate_meanings.append(cm); used_meanings.add(cm)
                if len(candidate_meanings) >= 3: break
        if len(candidate_meanings) >= 3: break
    if len(candidate_meanings) < 3:
        for group in shuffled_groups:
            gdata = vm.get_word_group(group['group_name'], group.get('dict_name', ''))
            if gdata and 'words' in gdata:
                for word in random.sample(gdata['words'], len(gdata['words'])):
                    if word.get('part_of_speech','') != correct_pos: continue
                    if word['word'].lower() == current_word.lower(): continue
                    cm = word.get('chinese_meaning','')
                    if cm == correct_meaning or cm in used_meanings or cm in used_wrong_meanings: continue
                    if has_too_many_common_chars(cm, correct_meaning): continue
                    candidate_meanings.append(cm); used_meanings.add(cm)
                    if len(candidate_meanings) >= 3: break
            if len(candidate_meanings) >= 3: break
    if len(candidate_meanings) < 3:
        for group in shuffled_groups:
            gdata = vm.get_word_group(group['group_name'], group.get('dict_name', ''))
            if gdata and 'words' in gdata:
                for word in gdata['words']:
                    if word.get('part_of_speech','') != correct_pos: continue
                    cm = word.get('chinese_meaning','')
                    if cm == correct_meaning or cm in used_meanings or cm in used_wrong_meanings: continue
                    candidate_meanings.append(cm); used_meanings.add(cm)
                    if len(candidate_meanings) >= 3: break
            if len(candidate_meanings) >= 3: break
    if len(candidate_meanings) < 3:
        all_ms = set()
        for group in shuffled_groups:
            gdata = vm.get_word_group(group['group_name'], group.get('dict_name', ''))
            if gdata and 'words' in gdata:
                for word in gdata['words']: all_ms.add(word.get('chinese_meaning',''))
        avail = list(all_ms - used_meanings - used_wrong_meanings - {correct_meaning})
        if avail: candidate_meanings.extend(random.sample(avail, min(3-len(candidate_meanings), len(avail))))
    while len(candidate_meanings) < 3: candidate_meanings.append(f'错{len(candidate_meanings)+1}')
    used_wrong_meanings.update(used_meanings)
    return random.sample(candidate_meanings, 3) if len(candidate_meanings) > 3 else candidate_meanings

def generate_treasure_answers(words):
    empty_seq = [5, 1, 2, 3, 4]
    treasure_counts = {1:0, 2:0, 3:0, 4:0, 5:0}
    answers, meanings, used_wrong_meanings = {}, {}, set()
    for i, w in enumerate(words):
        empty_card = empty_seq[i % 5]
        if i == 19:
            available = [c for c in range(1, 6) if c != empty_card]
            candidate = random.choice(available)
            sim = treasure_counts.copy(); sim[candidate] += 1
            if len([c for c, v in sim.items() if v == max(sim.values())]) > 1:
                for nc in [c for c in available if c != candidate]:
                    ns = treasure_counts.copy(); ns[nc] += 1
                    if len([c for c, v in ns.items() if v == max(ns.values())]) == 1: candidate = nc; break
            correct_card = candidate
        else:
            available = [c for c in range(1, 6) if treasure_counts[c] < 16 and c != empty_card] or [c for c in range(1, 6) if c != empty_card]
            correct_card = random.choice(available)
        answers[i] = correct_card; treasure_counts[correct_card] += 1
        meanings[i] = {}; cm = w.get('chinese_meaning',''); cp = w.get('part_of_speech',''); cw = w['word']
        meanings[i][str(correct_card)] = cm; meanings[i][str(empty_card)] = None
        wm = generate_wrong_meanings_for_web(cm, cp, cw, used_wrong_meanings)
        ac = [c for c in range(1, 6) if c != empty_card]; random.shuffle(ac)
        mc = [correct_card] + [c for c in ac if c != correct_card and len([correct_card] + [c]) <= 4]
        mi_idx = 0
        for card in range(1, 6):
            if card == empty_card or card == correct_card: continue
            if card in mc: meanings[i][str(card)] = wm[mi_idx] if mi_idx < len(wm) else f'错{mi_idx+1}'; mi_idx += 1
    true_treasure = max(treasure_counts, key=treasure_counts.get)
    return answers, meanings, true_treasure, treasure_counts