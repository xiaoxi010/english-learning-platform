# treasure_web.py - 盗宝大师网页版（完全复刻Tkinter版）
from flask import Blueprint, render_template, request, jsonify
from exam_base_web import prepare_basic_words, get_all_group_names, calculate_similarity
from vocabulary_manager import get_vocab_manager
import random, os, uuid, math
from settings_web import get_all_settings
treasure_bp = Blueprint('treasure', __name__)

PASS_SCORE = 46
FULL_SCORE = 50
PATTERN_NAME = '盗宝大师'

ALL_SKILLS = ['重置', '翻牌', '预言', '孤注一掷', '看破', '科技之星', '枫恬果实']
SKILL_INFO = {
    '重置': {'max': 3, 'desc': '刷新当前轮单词和选项'},
    '翻牌': {'max': 1, 'desc': '查看一个宝藏卡的正确次数'},
    '预言': {'max': 1, 'desc': '查看真宝藏的正确次数'},
    '孤注一掷': {'max': 1, 'desc': '挖宝选错时25%概率重选'},
    '看破': {'max': 2, 'desc': '查验某轮选择是否正确'},
    '科技之星': {'max': 1, 'desc': '选4个轮次，全对绿/错1黄/≥2红'},
    '枫恬果实': {'max': 1, 'desc': '在统计阶段对某轮使用，正确+1分，错误显示答案'}
}

TREASURE_NAMES = ['青山', '寒山', '沧山', '暮山', '尘山']

exam_sessions = {}

def prepare_treasure_words(today, yesterday):
    all_words = []
    seen = set()
    for g in get_vocab_manager().get_all_groups():
        if g['group_name'] in [today, yesterday]: continue
        gdata = get_vocab_manager().get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            for w in gdata['words']:
                key = (w['word'].lower(), w.get('chinese_meaning', ''))
                if key not in seen:
                    seen.add(key)
                    all_words.append(w)
    if len(all_words) < 20: return None, '词汇不足'
    return random.sample(all_words, 20), None


import math

# ============ 新增：字母相似度计算 ============
def calculate_word_similarity(word1, word2):
    if not word1 or not word2:
        return 0
    set1 = set(word1.lower())
    set2 = set(word2.lower())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    if union == 0:
        return 0
    return intersection / union

# ============ 新增：检查汉译是否有2个以上重复字 ============
def has_too_many_common_chars(text1, text2):
    if not text1 or not text2:
        return False
    filter_chars = ['的', '地', '得', '了', '在', '是', '有', '和', '与', '及', '或', '使', '让', '把', '被', '不', '错误']
    def filter_text(text):
        return ''.join([char for char in text if char not in filter_chars])
    t1 = filter_text(text1)
    t2 = filter_text(text2)
    if not t1 or not t2:
        return False
    common = set(t1) & set(t2)
    return len(common) >= 2

# ============ 新增：生成错误汉译（复刻Tkinter版） ============
def build_words_pool():
    """一次性加载全部单词，避免每轮重复查库"""
    words = []
    for g in get_vocab_manager().get_all_groups():
        gdata = get_vocab_manager().get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            words.extend(gdata['words'])
    return words


def generate_wrong_meanings_for_web(correct_meaning, correct_pos, current_word, used_wrong_meanings, words_pool=None):
    """生成错误答案 - 优先满足条件，如果找不到就放宽条件"""
    if words_pool is None:
        words_pool = build_words_pool()

    candidate_meanings = []
    used_meanings = set()
    current_lower = current_word.lower()

    def scan_words(check_similarity=False, check_common_chars=True, require_pos=True):
        shuffled = words_pool.copy()
        random.shuffle(shuffled)
        for word in shuffled:
            if require_pos and word.get('part_of_speech', '') != correct_pos:
                continue
            if word['word'].lower() == current_lower:
                continue
            if check_similarity and calculate_word_similarity(current_lower, word['word'].lower()) < 0.7:
                continue
            candidate_meaning = word.get('chinese_meaning', '')
            if (candidate_meaning == correct_meaning or
                    candidate_meaning in used_meanings or
                    candidate_meaning in used_wrong_meanings):
                continue
            if check_common_chars and has_too_many_common_chars(candidate_meaning, correct_meaning):
                continue
            candidate_meanings.append(candidate_meaning)
            used_meanings.add(candidate_meaning)
            if len(candidate_meanings) >= 3:
                break

    scan_words(check_similarity=True, check_common_chars=True, require_pos=True)
    if len(candidate_meanings) < 3:
        scan_words(check_similarity=False, check_common_chars=True, require_pos=True)
    if len(candidate_meanings) < 3:
        scan_words(check_similarity=False, check_common_chars=False, require_pos=True)
    if len(candidate_meanings) < 3:
        all_meanings = set()
        for word in words_pool:
            cm = word.get('chinese_meaning', '')
            if (cm != correct_meaning and
                    cm not in used_meanings and
                    cm not in used_wrong_meanings):
                all_meanings.add(cm)
        available = list(all_meanings - used_meanings)
        if available:
            needed = 3 - len(candidate_meanings)
            additional = random.sample(available, min(needed, len(available)))
            candidate_meanings.extend(additional)
            used_meanings.update(additional)

    if len(candidate_meanings) < 3:
        generic = ["错误翻译", "不正确", "意思不对", "不匹配", "翻译错误", "错误意思"]
        for g in generic:
            if len(candidate_meanings) >= 3:
                break
            if g not in candidate_meanings and g not in used_wrong_meanings:
                candidate_meanings.append(g)
                used_meanings.add(g)

    used_wrong_meanings.update(used_meanings)

    if len(candidate_meanings) > 3:
        return random.sample(candidate_meanings, 3)
    return candidate_meanings

def generate_treasure_answers(words):
    empty_seq = [5, 1, 2, 3, 4]
    treasure_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    answers = {}
    meanings = {}
    used_wrong_meanings = set()
    words_pool = build_words_pool()

    for i, w in enumerate(words):
        empty_card = empty_seq[i % 5]
         # 最后一轮特殊处理
        if i == 19:
            correct_card = find_best_treasure_for_last_round(treasure_counts, empty_card)
        else:
            available = [c for c in range(1, 6) if treasure_counts[c] < 16 and c != empty_card]
            if not available:
                available = [c for c in range(1, 6) if c != empty_card]
            correct_card = random.choice(available)
        answers[i] = correct_card
        treasure_counts[correct_card] += 1
        meanings[i] = {}
        cm = w.get('chinese_meaning', '')
        correct_pos = w.get('part_of_speech', '')
        current_word = w['word']

        meanings[i][str(correct_card)] = cm
        meanings[i][str(empty_card)] = None

        # 使用新的错误汉译生成函数
        wrong_meanings = generate_wrong_meanings_for_web(cm, correct_pos, current_word, used_wrong_meanings, words_pool)

        # 分配答案到宝藏卡
        available_cards = [c for c in range(1, 6) if c != empty_card]
        random.shuffle(available_cards)
        meaning_cards = [correct_card]
        for card in available_cards:
            if card != correct_card and len(meaning_cards) < 4:
                meaning_cards.append(card)
            if len(meaning_cards) >= 4:
                break

        meaning_index = 0
        for card in range(1, 6):
            if card == empty_card:
                continue  # 已经设为None
            elif card == correct_card:
                continue  # 已经设为cm
            elif card in meaning_cards and card != correct_card:
                if meaning_index < len(wrong_meanings):
                    meanings[i][str(card)] = wrong_meanings[meaning_index]
                    meaning_index += 1
                else:
                    meanings[i][str(card)] = f'错{meaning_index+1}'

    true_treasure = max(treasure_counts, key=treasure_counts.get)
    return answers, meanings, true_treasure, treasure_counts

def find_best_treasure_for_last_round(treasure_counts, empty_card):
    available = [c for c in range(1, 6) if c != empty_card]
    candidate = random.choice(available)
    
    sim = treasure_counts.copy()
    sim[candidate] += 1
    max_count = max(sim.values())
    max_treasures = [c for c, count in sim.items() if count == max_count]
    
    if len(max_treasures) == 1:
        return candidate
    
    other = [c for c in available if c != candidate]
    for new_candidate in other:
        new_sim = treasure_counts.copy()
        new_sim[new_candidate] += 1
        new_max = max(new_sim.values())
        new_max_t = [c for c, count in new_sim.items() if count == new_max]
        if len(new_max_t) == 1:
            return new_candidate
    
    results = {}
    for test in available:
        test_counts = treasure_counts.copy()
        test_counts[test] += 1
        test_max = max(test_counts.values())
        test_max_t = [c for c, count in test_counts.items() if count == test_max]
        results[test] = len(test_max_t)
    
    return min(results, key=results.get)

@treasure_bp.route('/api/treasure/start', methods=['POST'])
def start_exam():
    data = request.get_json()
    today = data.get('today_group', '').strip()
    yesterday = data.get('yesterday_group', '').strip()
    if not today or not yesterday: return jsonify({'success': False, 'message': '请选择今日和昨日单词组'})
    basic_words, error = prepare_basic_words(today, yesterday)
    if error: return jsonify({'success': False, 'message': error})
    treasure_words, error = prepare_treasure_words(today, yesterday)
    if error: return jsonify({'success': False, 'message': error})
    answers, meanings, true_treasure, treasure_counts = generate_treasure_answers(treasure_words)
    exam_id = str(uuid.uuid4())
    exam_sessions[exam_id] = {
        'basic': [{'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning']} for w in basic_words],
        'treasure_words': [{'word': w['word'], 'pos': w.get('part_of_speech',''), 'meaning': w.get('chinese_meaning','')} for w in treasure_words],
        'answers': answers, 'meanings': meanings, 'true_treasure': true_treasure,
        'treasure_counts': treasure_counts, 'today': today, 'yesterday': yesterday,
        'user_choices': {}, 'treasure_score': 0, 'current_round': 0,
        'skill_remaining': {}, 'selected_skills': [], 'found_true_treasure': False,
        'final_treasure_selected': None, 'basic_score': 0, 'basic_results': [], 'reset_count': 0
    }
    return jsonify({'success': True, 'exam_id': exam_id,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(basic_words)], 'total': len(basic_words)})


@treasure_bp.route('/api/treasure/submit_basic', methods=['POST'])
def submit_basic():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    answers = data.get('answers', {})
    words = es['basic']
    results, correct = [], 0
    for i, w in enumerate(words):
        ua = answers.get(str(i), '').strip()
        sim = calculate_similarity(ua, w['meaning'])
        ok = sim >= 2
        if ok: correct += 1
        results.append({'index': i, 'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning'],
                       'user_answer': ua, 'is_correct': ok, 'score': '1.00' if ok else '0.00',
                       'auto_status': 'correct' if sim>=2 else ('wrong' if sim==0 else 'uncertain')})
    es['basic_results'] = results; es['basic_score'] = correct
    for r in results:
        try:
            if r['is_correct']: get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else: get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except: pass
    return jsonify({'success': True, 'results': results, 'score': correct, 'total': len(words)})


@treasure_bp.route('/api/treasure/start_game', methods=['POST'])
def start_game():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    corrections = data.get('corrections', {})
    correct = 0
    for i, r in enumerate(es.get('basic_results', [])):
        if str(i) in corrections:
            r['is_correct'] = corrections[str(i)]
            r['score'] = '1.00' if corrections[str(i)] else '0.00'
        if r['is_correct']:
            correct += 1
        # 根据手动修正后的结果更新错题本
        try:
            if r['is_correct']:
                get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except: pass
    es['basic_score'] = correct
    selected = data.get('selected_skills', [])
    if len(selected) != 2: return jsonify({'success': False, 'message': '请选择2个技能'})
    es['selected_skills'] = selected
    es['skill_remaining'] = {s: SKILL_INFO[s]['max'] for s in selected}
    return jsonify({'success': True, 'selected_skills': selected, 'skill_remaining': es['skill_remaining'], 'basic_score': correct})


@treasure_bp.route('/api/treasure/get_round', methods=['POST'])
def get_round():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    ri = es['current_round']
    if ri >= 20: return jsonify({'success': False, 'game_over': True})
    w = es['treasure_words'][ri]
    empty_seq = [5, 1, 2, 3, 4]
    ec = empty_seq[ri % 5]
    return jsonify({'success': True, 'round': ri+1, 'total_rounds': 20,
        'word': w['word'], 'pos': w['pos'], 'empty_card': ec,
        'meanings': es['meanings'][ri], 'current_score': es['treasure_score'],
        'skill_remaining': es['skill_remaining']})


@treasure_bp.route('/api/treasure/submit_choice', methods=['POST'])
def submit_choice():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    ri = es['current_round']

    # ============ 重置：空位置不变，正确位置不变，只换单词和汉译，不进入下一轮 ============
    if data.get('use_reset') and es['skill_remaining'].get('重置', 0) > 0:
        es['skill_remaining']['重置'] -= 1
        es['reset_count'] += 1
        correct_card = es['answers'][ri]  # 正确位置不变
        empty_seq = [5, 1, 2, 3, 4]
        nec = empty_seq[ri % 5]  # 空位置不变

        # 收集所有可用单词后随机选择
        available_words = []
        current_word = es['treasure_words'][ri]['word']
        for g in get_vocab_manager().get_all_groups():
            if g['group_name'] in [es['today'], es['yesterday']]: continue
            gdata = get_vocab_manager().get_word_group(g['group_name'], g.get('dict_name', ''))
            if gdata and 'words' in gdata:
                for w in gdata['words']:
                    if w['word'] != current_word:
                        available_words.append(w)

        if available_words:
            nw = random.choice(available_words)
            es['treasure_words'][ri] = {'word': nw['word'], 'pos': nw.get('part_of_speech',''), 'meaning': nw.get('chinese_meaning','')}
            ncm = nw.get('chinese_meaning','')
            npos = nw.get('part_of_speech','')
            es['meanings'][ri][str(correct_card)] = ncm
            # 使用新的错误汉译生成函数
            nwp = generate_wrong_meanings_for_web(ncm, npos, nw['word'], set())
            noc = [c for c in range(1, 6) if c != correct_card and c != nec]
            for j, card in enumerate(noc):
                es['meanings'][ri][str(card)] = nwp[j] if j < len(nwp) else f'错{j+1}'

        # 不增加 current_round，返回当前轮信息
        return jsonify({'success': True, 'current_score': es['treasure_score'],
            'reset_done': True, 'skill_remaining': es['skill_remaining']})
    
    # ============ 正常选择 ============
    choice = data.get('choice', 0)
    correct_card = es['answers'][ri]
    is_correct = (choice == correct_card)
    if is_correct:
        es['treasure_score'] += 1
    es['user_choices'][str(ri)] = choice

    es['current_round'] += 1
    return jsonify({'success': True, 'current_score': es['treasure_score'],
        'next_round': es['current_round']+1 if es['current_round'] < 20 else None,
        'skill_remaining': es['skill_remaining']})


@treasure_bp.route('/api/treasure/use_skill', methods=['POST'])
def use_skill():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    skill = data.get('skill', '')
    if skill not in es['skill_remaining'] or es['skill_remaining'][skill] <= 0:
        return jsonify({'success': False, 'message': '技能不可用'})
    result = {}

    if skill == '翻牌':
        t = data.get('target', 1)
        cnt = sum(1 for i in range(20) if es['answers'][i] == t)
        es['skill_remaining'][skill] -= 1
        result = {'treasure': t, 'count': cnt}

    elif skill == '预言':
        cnt = sum(1 for i in range(20) if es['answers'][i] == es['true_treasure'])
        es['skill_remaining'][skill] -= 1
        result = {'count': cnt}

    elif skill == '看破':
        ri = data.get('round_idx', 0)
        ok = (es['user_choices'].get(str(ri)) == es['answers'][ri])
        es['skill_remaining'][skill] -= 1
        result = {'round': ri+1, 'is_correct': ok}

    elif skill == '科技之星':
        rounds = data.get('rounds', [])
        c = sum(1 for r in rounds if es['user_choices'].get(str(r)) == es['answers'][r])
        es['skill_remaining'][skill] -= 1
        result = {'correct': c, 'status': 'green' if c==4 else ('yellow' if c==3 else 'red')}

    elif skill == '枫恬果实':
        # 在S6统计阶段使用，对某轮进行判定
        ri = data.get('round_idx', 0)
        is_correct = (es['user_choices'].get(str(ri)) == es['answers'][ri])
        es['skill_remaining'][skill] -= 1
        if is_correct:
            es['treasure_score'] = min(es['treasure_score'] + 1, 20)
        result = {'is_correct': is_correct, 'correct_card': es['answers'][ri], 'round': ri+1}

    elif skill in ['孤注一掷', '重置']:
        result = {'available': True}

    return jsonify({'success': True, 'result': result, 'skill_remaining': es['skill_remaining']})


@treasure_bp.route('/api/treasure/dig', methods=['POST'])
def dig():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    selected = data.get('treasure', 1)
    is_correct = (selected == es['true_treasure'])
    gambled = False
    final_selected = selected
    final_is_correct = is_correct
    
    if not is_correct and es['skill_remaining'].get('孤注一掷', 0) > 0:
        es['skill_remaining']['孤注一掷'] -= 1
        gambled = True
        if random.random() < 0.25:
            final_selected = es['true_treasure']  # 25%选到真宝藏
        else:
            wrong_options = [c for c in range(1, 6) if c != es['true_treasure']]
            final_selected = random.choice(wrong_options)  # 75%选错误位置
        final_is_correct = (final_selected == es['true_treasure'])
    
    es['final_treasure_selected'] = final_selected
    es['found_true_treasure'] = final_is_correct
    total = es.get('basic_score', 0) + es['treasure_score']
    passed = total >= PASS_SCORE and final_is_correct
    return jsonify({'success': True, 'is_correct': final_is_correct, 'true_treasure': es['true_treasure'],
        'selected': final_selected, 'gambled': gambled, 'original_selected': selected,
        'total_score': total, 'is_passed': passed,
        'treasure_score': es['treasure_score'], 'basic_score': es.get('basic_score', 0)})


@treasure_bp.route('/api/treasure/final_report', methods=['POST'])
def final_report():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    total = es.get('basic_score', 0) + es['treasure_score']
    passed = total >= PASS_SCORE and es['found_true_treasure']
    ts = {1:0,2:0,3:0,4:0,5:0}
    for c in es['user_choices'].values():
        if c in ts: ts[c] += 1
    rounds = []
    for i in range(20):
        w = es['treasure_words'][i]
        uc = es['user_choices'].get(str(i), 0)
        is_correct = (uc == es['answers'][i])
        rounds.append({'round': i+1, 'word': w['word'], 'pos': w['pos'],
            'meaning': w['meaning'], 'correct_card': es['answers'][i],
            'user_choice': uc, 'is_correct': is_correct})
        # 错题本处理
        try:
            if is_correct:
                get_vocab_manager().remove_word_from_wrong_book(w['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(w['word'], w['pos'], w['meaning'])
        except: pass
    return jsonify({'success': True, 'basic_score': es.get('basic_score', 0),
        'treasure_score': es['treasure_score'], 'total_score': total, 'is_passed': passed,
        'true_treasure': es['true_treasure'], 'treasure_counts': es['treasure_counts'],
        'treasure_selects': ts, 'found_true_treasure': es['found_true_treasure'],
        'final_selected': es.get('final_treasure_selected'), 'rounds_detail': rounds,
        'basic_results': es.get('basic_results', []), 'today_group': es['today'],
        'selected_skills': es['selected_skills'], 'skill_remaining': es['skill_remaining']})
@treasure_bp.route('/exam/treasure')
def treasure_page():
    settings = get_all_settings()
    return render_template('treasure.html',
                         groups=get_all_group_names(),
                         pattern_name=PATTERN_NAME,
                         pass_score=PASS_SCORE, full_score=FULL_SCORE,
                         treasure_names=TREASURE_NAMES,
                         user_name=settings.get('user_name', ''),
                         student_id=settings.get('student_id', ''))
@treasure_bp.route('/api/treasure/export_png', methods=['POST'])
def export_png():
    data = request.get_json()
    try:
        from PIL import Image, ImageDraw, ImageFont
        import tempfile, base64
        from datetime import datetime

        basic_results = data.get('basic_results', [])
        treasure_results = data.get('treasure_results', [])
        total_score = float(data.get('total_score', 0))
        treasure_score = float(data.get('treasure_score', 0))
        basic_score = float(data.get('basic_score', 0))
        is_passed = bool(data.get('is_passed', False))
        today_group = data.get('today_group', '')
        user_name = data.get('user_name', '')
        student_id = data.get('student_id', '')
        true_treasure = data.get('true_treasure', 1)
        found_true_treasure = data.get('found_true_treasure', False)
        treasure_counts = data.get('treasure_counts', {})

        S = 5
        W, H = 1290 * S, 950 * S
        img = Image.new('RGB', (W, H), (26, 26, 42))
        d = ImageDraw.Draw(img)

        try:
            ft = ImageFont.truetype("msyh.ttc", 20 * S)
            fh = ImageFont.truetype("msyh.ttc", 12 * S)
            fi = ImageFont.truetype("msyh.ttc", 10 * S)
            ftm = ImageFont.truetype("msyh.ttc", 9 * S)
            fth = ImageFont.truetype("msyh.ttc", 10 * S)
            ftc = ImageFont.truetype("msyh.ttc", 9 * S)
            fe = ImageFont.truetype("arial.ttf", 9 * S)
        except:
            ft = fh = fi = ftm = fth = ftc = fe = ImageFont.load_default()

        def s(v): return int(v * S)

        # 标题
        title = "盗宝大师考试总成绩报告"
        d.text((W // 2, s(20)), title, fill=(255, 215, 0), font=ft, anchor="ma")

        # 上半：信息
        top_y = s(55)
        left_x = s(40)
        left_w = (W - s(80)) // 2 - s(10)
        top_h = s(130)
        d.rectangle([left_x, top_y, left_x + left_w, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)

        ix, iy = left_x + s(10), top_y + s(8)
        d.text((ix, iy), "姓名：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(42), iy), user_name, fill=(255, 255, 255), font=fi)
        d.text((ix + s(130), iy), "学号：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(175), iy), student_id, fill=(255, 255, 255), font=fi)
        iy += s(18)
        d.text((ix, iy), "今日组别：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(60), iy), today_group, fill=(255, 255, 255), font=fi)
        d.text((ix + s(130), iy), "版型：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(165), iy), "盗宝大师", fill=(255, 255, 255), font=fi)
        iy += s(18)
        bc = (46, 204, 113) if basic_score >= 18 else (231, 76, 96)
        sc = (46, 204, 113) if treasure_score >= 16 else (231, 76, 96)
        tc = (46, 204, 113) if is_passed else (231, 76, 96)
        d.text((ix, iy), f"基础词汇：{basic_score:.2f}/30", fill=bc, font=fh)
        d.text((ix + s(120), iy), f"盗宝大师：{treasure_score}/20", fill=sc, font=fh)
        iy += s(18)
        d.text((ix, iy), f"总得分：{total_score:.2f}/50", fill=tc, font=fh)
        iy += s(18)
        d.text((ix, iy), "真宝藏：", fill=(52, 152, 219), font=fh)
        true_name = TREASURE_NAMES[true_treasure - 1]
        true_count = treasure_counts.get(str(true_treasure), treasure_counts.get(true_treasure, 0))
        d.text((ix + s(55), iy), f"{true_name}", fill=(255, 215, 0), font=fh)
        d.text((ix + s(110), iy), f"找到：{'是' if found_true_treasure else '否'}", fill=tc, font=fh)
        iy += s(18)
        d.text((ix, iy), f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(149, 165, 166), font=ftm)

        # 照片
        rx = left_x + left_w + s(20)
        rw = left_w
        d.rectangle([rx, top_y, rx + rw, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
        pp = r"E:\vxcode数据文件\static\images\通过.png" if is_passed else r"E:\vxcode数据文件\static\images\挂科.png"
        if os.path.exists(pp):
            pi = Image.open(pp).resize((s(140), s(85)), Image.Resampling.LANCZOS)
            img.paste(pi, (rx + (rw - s(140)) // 2, top_y + (top_h - s(85)) // 2))
        else:
            d.text((rx + rw // 2, top_y + top_h // 2), "通过" if is_passed else "挂科", fill=tc, font=fh, anchor="mm")

        # 表格
        ty = top_y + top_h + s(15)
        cols4 = [s(140), s(50), s(130), s(50)]
        headers4 = ["单词", "词性", "汉译", "得分"]
        gap = s(12)

        hx = s(45)
        for grp in range(3):
            for ci, (hdr, cw) in enumerate(zip(headers4, cols4)):
                bg = (255, 215, 0) if ci == 0 else ((52, 152, 219) if ci == 1 else (42, 42, 58))
                d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm")
                hx += cw
            hx += gap

        all_words = []
        for r in basic_results:
            cl = (46, 204, 113) if r.get('is_correct') else (231, 76, 96)
            all_words.append({'word': r['word'], 'pos': r.get('pos', ''), 'meaning': r['meaning'], 'score': r.get('score', '1.00' if r.get('is_correct') else '0.00'), 'color': cl})
        while len(all_words) < 30:
            all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
        for r in treasure_results:
            cl = (46, 204, 113) if r.get('is_correct') else (231, 76, 96)
            all_words.append({'word': r['word'], 'pos': r.get('pos', ''), 'meaning': r['meaning'], 'score': '1.00' if r.get('is_correct') else '0.00', 'color': cl})
        while len(all_words) < 50:
            all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})

        ry = ty + s(25)
        rh = s(22)
        for row in range(17):
            bg_row = (42, 42, 58) if row % 2 == 0 else (37, 37, 53)
            d.rectangle([s(40), ry, s(40) + s(35), ry + rh], fill=(26, 26, 42), outline=(255, 255, 255), width=1)
            d.text((s(40) + s(17), ry + rh // 2), f"{(row+1):02d}", fill=(52, 152, 219), font=ftc, anchor="mm")
            cx_start = s(40) + s(35)
            for col in range(3):
                idx = row * 3 + col
                cx = cx_start + col * (sum(cols4) + gap)
                if idx < len(all_words):
                    w = all_words[idx]
                    vals = [w['word'], w['pos'], w['meaning'], w['score']]
                else:
                    vals = ['-', '-', '-', '-']
                    w = {'color': (127, 140, 141)}
                for ci, (cw, txt) in enumerate(zip(cols4, vals)):
                    d.rectangle([cx, ry, cx + cw, ry + rh], fill=bg_row, outline=(255, 255, 255), width=1)
                    fc = w['color'] if ci == 0 or ci == 3 else ((52, 152, 219) if ci == 1 else (255, 255, 255))
                    f = fe if (ci == 0 or ci == 3) else ftc
                    d.text((cx + cw // 2, ry + rh // 2), txt[:15], fill=fc, font=f, anchor="mm")
                    cx += cw
            ry += rh

        tmp = tempfile.gettempdir()
        fp = os.path.join(tmp, 'treasure_report.png')
        img.save(fp, dpi=(800, 800))
        with open(fp, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        os.remove(fp)
        return jsonify({'success': True, 'image': b64})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})