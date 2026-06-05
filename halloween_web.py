# halloween_web.py - 万圣之夜网页版（完整版，修复词汇加载）
from flask import Blueprint, render_template, request, jsonify
from exam_base_web import prepare_basic_words, get_all_group_names, calculate_similarity
from vocabulary_manager import get_vocab_manager
import random, os, uuid, math, json, difflib

halloween_bp = Blueprint('halloween', __name__)

PASS_SCORE = 43
FULL_SCORE = 50
PATTERN_NAME = '万圣之夜'

# ============ 游戏常量 ============
TOTAL_ROUNDS = 30
INITIAL_CRYSTALS = 50

SPELL_CARDS = [
    "圣骑士的馈赠", "云莱的蜜饯", "云莱的蜜饯",
    "小诗的悦耳琴音", "小诗的悦耳琴音", "小诗的悦耳琴音",
    "枫恬恬的晚曦", "梦柔柔的圣洁之光",
    "复苏神女玛丽娜", "复苏神女玛丽娜", "复苏神女玛丽娜",
    "启灵者伊丽莎白", "布鲁斯的晚宴", "布鲁斯的晚宴",
    "聆妙奇幻时空",
]

RESTRICTION_CARDS = [
    "奥古斯丁的机械臂", "蔡文姬的毒药", "魔域领主",
    "盗窃者罗娜", "盗窃者律法", "影月的毁灭之镰",
    "九幽的邪恶道士", "伊芙琳的堕落之血", "玉皇大帝",
    "宇伯言的阴阳置换", "伊格尼丝诡异契约", "刺客双鱼座",
    "汐羽的绝对领域", "伽顿法术反制", "刺客双鱼座",
]

UNKNOWN_CARDS = [
    "蔡文姬的毒药", "九幽的邪恶道士",
    "伊芙琳的堕落之血", "宇伯言的阴阳置换",
    "伊格尼丝诡异契约", "伽顿法术反制"
]

HAND_SPELL_CARDS = [
    "小诗的悦耳琴音", "枫恬恬的晚曦", "梦柔柔的圣洁之光",
    "复苏神女玛丽娜", "启灵者伊丽莎白", "布鲁斯的晚宴",
    "聆妙奇幻时空"
]

CHOICE_CARDS = [
    {"name": "开门", "type": "选择卡"},
    {"name": "不开门", "type": "选择卡"}
]

exam_sessions = {}


# ============ 词汇加载函数（已修复） ============

def load_vocabulary_from_db():
    """从数据库加载所有激活词典的词汇（使用VocabularyManager）"""
    all_vocab = []
    
    try:
        # 获取所有激活的词典
        active_dicts = get_vocab_manager().get_active_dictionaries()
        print(f"[万圣之夜] 激活词典: {active_dicts}")
        
        if not active_dicts:
            print("[万圣之夜] 警告：没有激活的词典！")
            return all_vocab
        
        # 遍历所有单词组
        all_groups = get_vocab_manager().get_all_groups()
        print(f"[万圣之夜] 找到 {len(all_groups)} 个单词组")
        
        seen_words = set()
        
        for group in all_groups:
            group_name = group['group_name']
            dict_name = group.get('dict_name', '')
            
            if dict_name not in active_dicts:
                continue
            
            # 跳过错题词典
            if dict_name == 'A-错题词典':
                continue
            
            group_data = get_vocab_manager().get_word_group(group_name, dict_name)
            if not group_data or 'words' not in group_data:
                continue
            
            for w in group_data['words']:
                word_key = w['word'].lower()
                if word_key in seen_words:
                    continue
                seen_words.add(word_key)
                
                meaning = w.get('chinese_meaning', '')
                meanings = []
                if meaning:
                    meaning = meaning.replace('；', ';')
                    for part in meaning.split(';'):
                        part = part.strip()
                        if part:
                            meanings.append(part)
                
                if not meanings:
                    meanings = ["无汉译"]
                
                all_vocab.append({
                    'word': w['word'],
                    'part_of_speech': w.get('part_of_speech', ''),
                    'meanings': meanings,
                    'dict_name': dict_name
                })
        
        print(f"[万圣之夜] 成功加载 {len(all_vocab)} 个词汇")
        
        if all_vocab:
            for i in range(min(3, len(all_vocab))):
                v = all_vocab[i]
                print(f"  样本: {v['word']} ({v['part_of_speech']}) - {v['meanings']}")
        else:
            print("[万圣之夜] 词汇为空！请检查数据库是否有单词数据")
    
    except Exception as e:
        print(f"[万圣之夜] 加载词汇失败: {e}")
        import traceback
        traceback.print_exc()
    
    return all_vocab


# ============ 辅助函数 ============

def get_chinese_chars_from_meanings(meanings):
    chars = set()
    for meaning in meanings:
        for char in meaning:
            if '\u4e00' <= char <= '\u9fff':
                chars.add(char)
    return chars


def has_common_chinese_chars(meanings1, meanings2):
    if not meanings1 or not meanings2:
        return False
    chars1 = get_chinese_chars_from_meanings(meanings1)
    chars2 = get_chinese_chars_from_meanings(meanings2)
    return len(chars1.intersection(chars2)) > 0


def get_similar_word_with_different_meaning(all_vocab, original_word, pos, exclude_words=None):
    if not all_vocab:
        return None
    if exclude_words is None:
        exclude_words = set()
    
    original_meanings = []
    for v in all_vocab:
        if v['word'] == original_word:
            original_meanings = v['meanings']
            break
    
    candidates = []
    for word_data in all_vocab:
        word = word_data['word']
        if word in exclude_words or word == original_word or word_data['part_of_speech'] != pos:
            continue
        similarity = difflib.SequenceMatcher(None, original_word.lower(), word.lower()).ratio()
        if similarity < 0.7:
            continue
        if not has_common_chinese_chars(original_meanings, word_data['meanings']):
            candidates.append(word_data)
    
    if candidates:
        return random.choice(candidates)
    
    pos_candidates = [w for w in all_vocab if w['part_of_speech'] == pos and w['word'] not in exclude_words]
    if pos_candidates:
        return random.choice(pos_candidates)
    return None


def find_exact_match_meaning_strict(all_vocab, question_word, exclude_words):
    question_meanings = question_word['meanings']
    for word_data in all_vocab:
        word = word_data['word']
        if word in exclude_words or word == question_word['word']:
            continue
        for q_meaning in question_meanings:
            for c_meaning in word_data['meanings']:
                if q_meaning == c_meaning:
                    return True, word_data
    return False, None


# ============ 页面路由 ============

@halloween_bp.route('/exam/halloween')
def halloween_page():
    return render_template('halloween.html',
                         groups=get_all_group_names(),
                         pattern_name=PATTERN_NAME,
                         pass_score=PASS_SCORE, full_score=FULL_SCORE)


# ============ 考试API ============

@halloween_bp.route('/api/halloween/start', methods=['POST'])
def start_exam():
    data = request.get_json()
    today = data.get('today_group', '').strip()
    yesterday = data.get('yesterday_group', '').strip()
    
    if not today or not yesterday:
        return jsonify({'success': False, 'message': '请选择今日和昨日单词组'})
    
    basic_words, error = prepare_basic_words(today, yesterday)
    if error:
        return jsonify({'success': False, 'message': error})
    
    exam_id = str(uuid.uuid4())
    exam_sessions[exam_id] = {
        'basic': [{'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning']} for w in basic_words],
        'today': today,
        'yesterday': yesterday,
        'phase': 'basic',
        'basic_score': 0,
        'basic_results': [],
        'game_state': None
    }
    
    return jsonify({
        'success': True,
        'exam_id': exam_id,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(basic_words)],
        'total': len(basic_words)
    })


@halloween_bp.route('/api/halloween/submit_basic', methods=['POST'])
def submit_basic():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    
    answers = data.get('answers', {})
    words = es['basic']
    results, correct = [], 0
    
    for i, w in enumerate(words):
        ua = answers.get(str(i), '').strip()
        sim = calculate_similarity(ua, w['meaning'])
        ok = sim >= 2
        if ok:
            correct += 1
        results.append({
            'index': i, 'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning'],
            'user_answer': ua, 'is_correct': ok, 'score': '1.00' if ok else '0.00',
            'auto_status': 'correct' if sim >= 2 else ('wrong' if sim == 0 else 'uncertain')
        })
    
    es['basic_results'] = results
    es['basic_score'] = correct
    
    for r in results:
        try:
            if r['is_correct']:
                get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass
    
    return jsonify({'success': True, 'results': results, 'score': correct, 'total': len(words)})


# ============ 游戏初始化API ============

@halloween_bp.route('/api/halloween/init_game', methods=['POST'])
def init_game():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    
    corrections = data.get('corrections', {})
    correct = 0
    for i, r in enumerate(es.get('basic_results', [])):
        if str(i) in corrections:
            r['is_correct'] = corrections[str(i)]
            r['score'] = '1.00' if corrections[str(i)] else '0.00'
        if r['is_correct']:
            correct += 1
        try:
            if r['is_correct']:
                get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass
    es['basic_score'] = correct
    
    all_vocab = load_vocabulary_from_db()
    
    if not all_vocab:
        return jsonify({
            'success': False,
            'message': '词汇数据库为空！请先在词汇管理系统中添加单词数据。\n需要：激活的词典 + 单词组 + 单词'
        })
    
    deck = SPELL_CARDS + RESTRICTION_CARDS
    random.shuffle(deck)
    
    game_state = {
        'current_round': 1,
        'total_rounds': TOTAL_ROUNDS,
        'crystals': INITIAL_CRYSTALS,
        'candies': 0,
        'unknown_cards': 0,
        'deck': deck,
        'used_words': [],
        'hand_spell_cards': [],
        'game_records': [],
        'all_vocabulary': all_vocab,
        'game_effects': {
            'augustine_arm_rounds': 0,
            'vocab_score_deduction': 0,
            'vocab_score_bonus': 0,
            'disable_not_open_next_round': False,
            'empty_hints_next_round': False,
            'disable_spell_next_round': False,
            'disable_spell_this_round': False,
            'disable_left_hand_next_round': False,
            'disable_left_hand_this_round': False,
            'zork_counter_active': False,
            'yuboyan_activated': False,
            'yuboyan_triggered': False,
            'demon_lord_active_this_round': False,
            'meng_rourou_active': False,
            'evelyn_failed_proof': False,
            'skip_this_round': False,
            'auto_select_correct': False,
            'need_selection': False,
            'selection_options': [],
            'game_phase': 'waiting',
            'spell_destroyed_count': 0,
        },
        'unknown_card_states': {},
        'current_round_info': None,
        'round_in_progress': False,
        'word_slots': [],
        'correct_answer_index': -1,
    }
    
    es['game_state'] = game_state
    es['phase'] = 'game'
    
    return jsonify({
        'success': True,
        'basic_score': correct,
        'vocab_count': len(all_vocab),
        'initial_state': {
            'current_round': game_state['current_round'],
            'total_rounds': game_state['total_rounds'],
            'crystals': game_state['crystals'],
            'candies': game_state['candies'],
            'unknown_cards': game_state['unknown_cards'],
            'hand_spell_count': len(game_state['hand_spell_cards']),
            'deck_count': len(game_state['deck']),
            'game_phase': game_state['game_effects']['game_phase'],
        }
    })


# ============ 游戏核心API ============

def get_game_display_state(gs):
    return {
        'current_round': gs['current_round'],
        'total_rounds': gs['total_rounds'],
        'crystals': gs['crystals'],
        'candies': gs['candies'],
        'unknown_cards': gs['unknown_cards'],
        'hand_spell_count': len(gs['hand_spell_cards']),
        'deck_count': len(gs['deck']),
        'game_phase': gs['game_effects']['game_phase'],
    }


def get_hand_state(gs):
    hand_cards = []
    for i, spell_name in enumerate(gs['hand_spell_cards'][:4]):
        hand_cards.append({
            'position': i,
            'card_name': spell_name,
            'card_type': '法术卡',
            'disabled': (gs['game_effects'].get('disable_spell_this_round', False) or
                        gs['game_effects'].get('disable_left_hand_this_round', False))
        })
    for i, choice in enumerate(CHOICE_CARDS):
        pos = 4 + i
        disabled = False
        if choice['name'] == '不开门' and gs['game_effects'].get('demon_lord_active_this_round', False):
            disabled = True
        hand_cards.append({
            'position': pos,
            'card_name': choice['name'],
            'card_type': choice['type'],
            'disabled': disabled
        })
    return hand_cards


def refresh_word_slots(gs):
    all_vocab = gs['all_vocabulary']
    used_words = set(gs.get('used_words', []))
    current_card = gs['deck'][0] if gs['deck'] else None
    is_spell = current_card in SPELL_CARDS if current_card else True
    show_correct = is_spell
    
    available = [w for w in all_vocab if w['word'] not in used_words]
    if not available:
        gs['used_words'] = []
        available = all_vocab.copy()
    
    question_word = random.choice(available).copy()
    gs['used_words'].append(question_word['word'])
    
    gs['current_round_info'] = gs.get('current_round_info', {})
    gs['current_round_info']['question_word'] = {
        'word': question_word['word'],
        'part_of_speech': question_word['part_of_speech'],
        'meanings': question_word['meanings']
    }
    
    word_slots = []
    slot_words = {}
    used_hint = {question_word['word']}
    correct_answer_index = -1
    
    if show_correct:
        found, exact_word = find_exact_match_meaning_strict(all_vocab, question_word, used_hint)
        if found:
            correct_answer_index = random.randint(1, 4)
            if correct_answer_index in [1, 3]:
                slot_words[correct_answer_index] = exact_word.copy()
                used_hint.add(exact_word['word'])
            else:
                slot_words[correct_answer_index] = question_word.copy()
        else:
            correct_answer_index = random.choice([2, 4])
            slot_words[correct_answer_index] = question_word.copy()
    
    gs['correct_answer_index'] = correct_answer_index
    
    for i in range(5):
        if i == 0:
            slot = {
                'index': i, 'display_text': question_word['word'],
                'slot_type': 'question', 'word': question_word['word'],
                'meanings': question_word['meanings']
            }
        else:
            if gs['game_effects'].get('empty_hints_next_round', False):
                slot = {'index': i, 'display_text': '玉皇大帝', 'slot_type': 'emperor', 'word': '', 'meanings': []}
            elif gs['game_effects'].get('augustine_arm_rounds', 0) > 0 and i == 4:
                slot = {'index': i, 'display_text': '奥古斯丁的机械臂', 'slot_type': 'augustine', 'word': '', 'meanings': []}
            elif i in slot_words:
                wd = slot_words[i]
                display = wd['word'] if i in [1, 3] else (random.choice(wd['meanings']) if wd['meanings'] else '无汉译')
                slot = {
                    'index': i, 'display_text': display, 'slot_type': 'hint',
                    'word': wd['word'], 'meanings': wd['meanings'],
                    'is_correct': (i == correct_answer_index)
                }
                used_hint.add(wd['word'])
            else:
                wrong_word = get_similar_word_with_different_meaning(all_vocab, question_word['word'], question_word['part_of_speech'], used_hint)
                if wrong_word:
                    used_hint.add(wrong_word['word'])
                    display = wrong_word['word'] if i in [1, 3] else (random.choice(wrong_word['meanings']) if wrong_word['meanings'] else '无汉译')
                    slot = {
                        'index': i, 'display_text': display, 'slot_type': 'hint',
                        'word': wrong_word['word'], 'meanings': wrong_word['meanings'],
                        'is_correct': False
                    }
                else:
                    slot = {'index': i, 'display_text': '无数据', 'slot_type': 'hint', 'word': '', 'meanings': [], 'is_correct': False}
        word_slots.append(slot)
    
    gs['word_slots'] = word_slots
    gs['current_round_info']['word_slots'] = [
        {'slot_index': s['index'], 'display_text': s['display_text'], 'slot_type': s['slot_type'],
         'word': s.get('word', ''), 'meanings': s.get('meanings', [])}
        for s in word_slots
    ]


@halloween_bp.route('/api/halloween/start_round', methods=['POST'])
def start_round():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es or not es.get('game_state'):
        return jsonify({'success': False, 'message': '游戏未初始化'})
    
    gs = es['game_state']
    
    if gs['current_round'] > gs['total_rounds']:
        return jsonify({'success': True, 'game_over': True})
    
    gs['round_in_progress'] = True
    gs['game_effects']['game_phase'] = 'choose_door'
    
    gs['current_round_info'] = {
        'round': gs['current_round'],
        'start_crystals': gs['crystals'],
        'start_candies': gs['candies'],
        'card': gs['deck'][0] if gs['deck'] else None,
        'question_word': None,
        'word_slots': [],
        'door_selection': None,
        'result': None,
    }
    
    refresh_word_slots(gs)
    
    return jsonify({
        'success': True,
        'round': gs['current_round'],
        'total_rounds': gs['total_rounds'],
        'crystals': gs['crystals'],
        'candies': gs['candies'],
        'unknown_cards': gs['unknown_cards'],
        'deck_count': len(gs['deck']),
        'word_slots': gs['word_slots'],
        'hand_cards': get_hand_state(gs),
        'game_phase': gs['game_effects']['game_phase'],
        'demon_lord_active': gs['game_effects'].get('demon_lord_active_this_round', False),
        'yuboyan_active': gs['game_effects'].get('yuboyan_activated', False),
        'empty_hints': gs['game_effects'].get('empty_hints_next_round', False),
        'disable_spell': gs['game_effects'].get('disable_spell_this_round', False),
    })


# ============ 选择处理API ============

@halloween_bp.route('/api/halloween/make_choice', methods=['POST'])
def make_choice():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es or not es.get('game_state'):
        return jsonify({'success': False, 'message': '游戏未初始化'})
    
    gs = es['game_state']
    choice = data.get('choice', '')
    
    if gs['game_effects']['game_phase'] != 'choose_door':
        return jsonify({'success': False, 'message': '当前不能选择开门/不开门'})
    
    if choice == '不开门' and gs['game_effects'].get('demon_lord_active_this_round', False):
        return jsonify({'success': False, 'message': '魔域领主效果：不开门卡被禁用！'})
    
    # 宇伯言反转
    if gs['game_effects'].get('yuboyan_activated', False):
        gs['game_effects']['yuboyan_triggered'] = True
        gs['unknown_cards'] = max(0, gs['unknown_cards'] - 1)
        choice = '不开门' if choice == '开门' else '开门'
    
    if choice == '开门':
        return handle_open_door(gs)
    else:
        return handle_not_open_door(gs)


def handle_open_door(gs):
    gs['game_effects']['game_phase'] = 'post_door'
    gs['current_round_info']['door_selection'] = '开门'
    
    current_card = gs['deck'][0] if gs['deck'] else None
    
    if current_card in SPELL_CARDS:
        gs['current_round_info']['result'] = '正确'
    else:
        gs['current_round_info']['result'] = '错误'
    
    gs['current_round_info']['end_crystals'] = gs['crystals']
    gs['current_round_info']['end_candies'] = gs['candies']
    gs['game_records'].append(gs['current_round_info'].copy())
    
    # 伊格尼丝诡异契约
    if gs['game_effects'].get('clear_sky_next_round', False):
        gs['unknown_cards'] = max(0, gs['unknown_cards'] - 1)
        gs['game_effects']['clear_sky_next_round'] = False
        is_spell = current_card in SPELL_CARDS
        if not is_spell:
            gs['candies'] = max(0, gs['candies'] - 6)
        else:
            gs['candies'] += 2
    
    result = process_card_effect(gs, current_card)
    
    if gs['deck']:
        gs['deck'].pop(0)
    
    return jsonify({
        'success': True,
        'choice_made': '开门',
        'card_drawn': current_card,
        'card_effect': result.get('effect', ''),
        'new_crystals': gs['crystals'],
        'new_candies': gs['candies'],
        'new_unknown': gs['unknown_cards'],
        'hand_spell_cards': gs['hand_spell_cards'][:4],
        'need_selection': result.get('need_selection', False),
        'selection_options': gs['game_effects'].get('selection_options', []),
        'next_action': 'wait_for_next_round',
        'wait_time': 3000
    })


def handle_not_open_door(gs):
    if gs['crystals'] < 1:
        return jsonify({'success': False, 'message': '水晶不足'})
    
    gs['game_effects']['game_phase'] = 'post_door'
    gs['crystals'] -= 1
    gs['current_round_info']['door_selection'] = '不开门'
    gs['current_round_info']['result'] = '跳过'
    gs['current_round_info']['end_crystals'] = gs['crystals']
    gs['current_round_info']['end_candies'] = gs['candies']
    gs['game_records'].append(gs['current_round_info'].copy())
    
    # 伊格尼丝诡异契约
    if gs['game_effects'].get('clear_sky_next_round', False):
        gs['unknown_cards'] = max(0, gs['unknown_cards'] - 1)
        gs['game_effects']['clear_sky_next_round'] = False
        current_card = gs['deck'][0] if gs['deck'] else None
        is_spell = current_card in SPELL_CARDS
        if is_spell:
            gs['candies'] = max(0, gs['candies'] - 6)
        else:
            gs['candies'] += 2
    
    if gs['deck']:
        gs['deck'].pop(0)
    
    return jsonify({
        'success': True,
        'choice_made': '不开门',
        'new_crystals': gs['crystals'],
        'new_candies': gs['candies'],
        'new_unknown': gs['unknown_cards'],
        'next_action': 'wait_for_next_round',
        'wait_time': 3000
    })


# ============ 卡牌效果处理 ============

def process_card_effect(gs, card_name):
    result = {'effect': '', 'type': 'unknown'}
    
    if not card_name:
        return result
    
    # 梦柔柔免疫
    if gs['game_effects'].get('meng_rourou_active', False):
        if card_name in UNKNOWN_CARDS or card_name in RESTRICTION_CARDS:
            gs['candies'] += 2
            result['effect'] = f'梦柔柔免疫：{card_name} → 获得2糖果'
            return result
    
    if card_name == '圣骑士的馈赠':
        gs['candies'] += 2
        result['effect'] = '获得2糖果'
    elif card_name == '云莱的蜜饯':
        gs['candies'] += 3
        result['effect'] = '获得3糖果'
    elif card_name == '奥古斯丁的机械臂':
        gs['game_effects']['augustine_arm_rounds'] = 3
        gs['candies'] = max(0, gs['candies'] - 2)
        gs['crystals'] -= 2
        result['effect'] = '奥古斯丁的机械臂：接下来3轮第5卡槽被覆盖，扣除2糖果2水晶'
    elif card_name == '蔡文姬的毒药':
        gs['game_effects']['vocab_score_deduction'] += 1
        gs['crystals'] -= 1
        gs['unknown_cards'] += 1
        result['effect'] = '未知卡：基础词汇成绩-1'
    elif card_name == '九幽的邪恶道士':
        gs['game_effects']['vocab_score_deduction'] += 2
        gs['crystals'] -= 1
        gs['unknown_cards'] += 1
        result['effect'] = '未知卡：基础词汇成绩-2'
    elif card_name == '伊芙琳的堕落之血':
        gs['game_effects']['evelyn_failed_proof'] = True
        gs['crystals'] -= 1
        gs['unknown_cards'] += 1
        result['effect'] = '未知卡：伊芙琳的堕落之血已触发'
    elif card_name == '魔域领主':
        gs['candies'] = max(0, gs['candies'] - 3)
        gs['game_effects']['disable_not_open_next_round'] = True
        gs['crystals'] -= 2
        result['effect'] = '魔域领主：扣除3糖果，下一轮禁用不开门'
    elif card_name == '盗窃者罗娜':
        gs['candies'] = max(0, gs['candies'] - 2)
        gs['crystals'] -= 2
        result['effect'] = '盗窃者罗娜：扣除2糖果2水晶'
    elif card_name == '盗窃者律法':
        gs['candies'] = max(0, gs['candies'] - 3)
        gs['crystals'] -= 2
        result['effect'] = '盗窃者律法：扣除3糖果2水晶'
    elif card_name == '影月的毁灭之镰':
        gs['candies'] = max(0, gs['candies'] - 3)
        gs['crystals'] -= 2
        if gs['hand_spell_cards']:
            destroyed = gs['hand_spell_cards'].pop(random.randint(0, len(gs['hand_spell_cards']) - 1))
            gs['game_effects']['spell_destroyed_count'] += 1
            result['effect'] = f'影月的毁灭之镰：扣除3糖果，摧毁"{destroyed}"'
        else:
            gs['crystals'] = max(0, gs['crystals'] - 4)
            result['effect'] = '影月的毁灭之镰：扣除3糖果4水晶'
    elif card_name == '玉皇大帝':
        gs['candies'] = max(0, gs['candies'] - 2)
        gs['game_effects']['empty_hints_next_round'] = True
        gs['crystals'] -= 2
        result['effect'] = '玉皇大帝：下一轮提示显示"玉皇大帝"'
    elif card_name == '宇伯言的阴阳置换':
        gs['game_effects']['yuboyan_activated'] = True
        gs['crystals'] -= 1
        gs['unknown_cards'] += 1
        result['effect'] = '未知卡：下一轮开门/不开门将反转'
    elif card_name == '伊格尼丝诡异契约':
        gs['game_effects']['clear_sky_next_round'] = True
        gs['crystals'] -= 1
        gs['unknown_cards'] += 1
        result['effect'] = '未知卡：下一轮选错扣6糖，选对得2糖'
    elif card_name == '刺客双鱼座':
        gs['candies'] = max(0, gs['candies'] - 2)
        gs['crystals'] = max(0, gs['crystals'] - 6)
        result['effect'] = '刺客双鱼座：扣除2糖果6水晶'
    elif card_name == '汐羽的绝对领域':
        gs['candies'] = max(0, gs['candies'] - 2)
        gs['game_effects']['disable_spell_next_round'] = True
        gs['game_effects']['disable_left_hand_next_round'] = True
        gs['crystals'] -= 2
        result['effect'] = '汐羽的绝对领域：下一轮禁止使用法术卡'
    elif card_name == '伽顿法术反制':
        gs['game_effects']['zork_counter_active'] = True
        gs['crystals'] = max(0, gs['crystals'] - 5)
        gs['unknown_cards'] += 1
        result['effect'] = '未知卡：伽顿法术反制已激活'
    
    # 法术卡加入手牌
    if card_name in HAND_SPELL_CARDS and len(gs['hand_spell_cards']) < 4:
        if card_name not in gs['hand_spell_cards']:
            gs['hand_spell_cards'].append(card_name)
    
    return result


@halloween_bp.route('/api/halloween/use_spell', methods=['POST'])
def use_spell():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es or not es.get('game_state'):
        return jsonify({'success': False, 'message': '游戏未初始化'})
    
    gs = es['game_state']
    card_name = data.get('card_name', '')
    
    if card_name not in gs['hand_spell_cards']:
        return jsonify({'success': False, 'message': '手牌中没有这张卡'})
    
    if gs['game_effects'].get('disable_spell_this_round', False):
        return jsonify({'success': False, 'message': '当前轮禁止使用法术卡'})
    
    # 伽顿法术反制
    if gs['game_effects'].get('zork_counter_active', False) and not gs['game_effects'].get('meng_rourou_active', False):
        gs['game_effects']['zork_counter_active'] = False
        gs['hand_spell_cards'].remove(card_name)
        return jsonify({
            'success': True,
            'countered': True,
            'message': f'伽顿法术反制："{card_name}"被无效化！',
            'new_crystals': gs['crystals'],
            'new_candies': gs['candies'],
            'new_hand': gs['hand_spell_cards'][:4]
        })
    
    gs['hand_spell_cards'].remove(card_name)
    
    # 处理法术卡效果
    result_effect = ''
    need_selection = False
    
    if card_name == '小诗的悦耳琴音':
        if gs['crystals'] >= 4:
            gs['crystals'] -= 4
            gs['candies'] += 2
            result_effect = '小诗的悦耳琴音：刷新题目，获得2糖果'
        else:
            result_effect = '水晶不足'
    elif card_name == '启灵者伊丽莎白':
        if gs['crystals'] >= 1:
            gs['crystals'] -= 1
            gs['candies'] += 2
            gs['game_effects']['skip_this_round'] = True
            result_effect = '启灵者伊丽莎白：获得2糖果，跳过本回合'
        else:
            result_effect = '水晶不足'
    elif card_name == '梦柔柔的圣洁之光':
        if gs['crystals'] >= 9:
            gs['crystals'] -= 9
            gs['candies'] += 2
            gs['game_effects']['meng_rourou_active'] = True
            result_effect = '梦柔柔的圣洁之光：免疫本轮限制卡'
        else:
            result_effect = '水晶不足'
    elif card_name == '枫恬恬的晚曦':
        if gs['crystals'] >= 8:
            gs['crystals'] -= 8
            gs['game_effects']['need_selection'] = True
            gs['game_effects']['selection_options'] = ['枯木逢春', '枫恬恬的裁决']
            need_selection = True
            result_effect = '请选择效果'
        else:
            result_effect = '水晶不足'
    elif card_name == '复苏神女玛丽娜':
        if gs['crystals'] >= 1:
            gs['crystals'] -= 1
            gs['game_effects']['need_selection'] = True
            gs['game_effects']['selection_options'] = ['圣骑士的馈赠', '玛丽娜的赐福']
            need_selection = True
            result_effect = '请选择效果'
        else:
            result_effect = '水晶不足'
    elif card_name == '布鲁斯的晚宴':
        if gs['crystals'] >= 3:
            gs['crystals'] -= 3
            gs['game_effects']['need_selection'] = True
            gs['game_effects']['selection_options'] = ['圣骑士的馈赠', '布鲁斯的黑暗料理']
            need_selection = True
            result_effect = '请选择效果'
        else:
            result_effect = '水晶不足'
    elif card_name == '聆妙奇幻时空':
        if gs['crystals'] >= 7:
            gs['crystals'] -= 7
            gs['crystals'] += 22
            gs['candies'] += 2
            for spell in gs['hand_spell_cards'][:]:
                if len(gs['hand_spell_cards']) < 4:
                    gs['hand_spell_cards'].append(spell)
            result_effect = '聆妙奇幻时空：获得2糖果，恢复22水晶'
        else:
            result_effect = '水晶不足'
    
    return jsonify({
        'success': True,
        'spell_used': card_name,
        'effect': result_effect,
        'need_selection': need_selection,
        'selection_options': gs['game_effects'].get('selection_options', []),
        'new_crystals': gs['crystals'],
        'new_candies': gs['candies'],
        'new_hand': gs['hand_spell_cards'][:4]
    })


@halloween_bp.route('/api/halloween/make_selection', methods=['POST'])
def make_selection():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es or not es.get('game_state'):
        return jsonify({'success': False, 'message': '游戏未初始化'})
    
    gs = es['game_state']
    choice = data.get('choice', '')
    
    if not gs['game_effects'].get('need_selection', False):
        return jsonify({'success': False, 'message': '当前不需要选择'})
    
    result_effect = ''
    
    if choice == '枯木逢春':
        gs['game_effects']['vocab_score_bonus'] += 2
        result_effect = '枯木逢春：基础词汇得分+2'
    elif choice == '枫恬恬的裁决':
        gs['candies'] += 4
        gs['game_effects']['auto_select_correct'] = True
        result_effect = '枫恬恬的裁决：获得4糖果'
    elif choice == '圣骑士的馈赠':
        gs['candies'] += 2
        result_effect = '圣骑士的馈赠：获得2糖果'
    elif choice == '玛丽娜的赐福':
        gs['crystals'] += 6
        result_effect = '玛丽娜的赐福：获得6水晶'
    elif choice == '布鲁斯的黑暗料理':
        available = [s for s in SPELL_CARDS if s != '布鲁斯的晚宴' and s not in gs['hand_spell_cards']]
        if available and len(gs['hand_spell_cards']) < 4:
            random_spell = random.choice(available)
            gs['hand_spell_cards'].append(random_spell)
            result_effect = f'布鲁斯的黑暗料理：获得"{random_spell}"'
        else:
            result_effect = '布鲁斯的黑暗料理：手牌已满'
    
    gs['game_effects']['need_selection'] = False
    gs['game_effects']['selection_options'] = []
    
    return jsonify({
        'success': True,
        'effect': result_effect,
        'new_crystals': gs['crystals'],
        'new_candies': gs['candies'],
        'new_hand': gs['hand_spell_cards'][:4]
    })


# ============ 下一轮 ============

@halloween_bp.route('/api/halloween/next_round', methods=['POST'])
def next_round():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es or not es.get('game_state'):
        return jsonify({'success': False, 'message': '游戏未初始化'})
    
    gs = es['game_state']
    
    # 应用持续效果
    if gs['game_effects']['augustine_arm_rounds'] > 0:
        gs['game_effects']['augustine_arm_rounds'] -= 1
    
    gs['game_effects']['demon_lord_active_this_round'] = gs['game_effects'].get('disable_not_open_next_round', False)
    gs['game_effects']['disable_not_open_next_round'] = False
    
    gs['game_effects']['disable_spell_this_round'] = gs['game_effects'].get('disable_spell_next_round', False)
    gs['game_effects']['disable_left_hand_this_round'] = gs['game_effects'].get('disable_left_hand_next_round', False)
    gs['game_effects']['disable_spell_next_round'] = False
    gs['game_effects']['disable_left_hand_next_round'] = False
    
    gs['game_effects']['empty_hints_next_round'] = False
    gs['game_effects']['meng_rourou_active'] = False
    gs['game_effects']['need_selection'] = False
    gs['game_effects']['selection_options'] = []
    gs['game_effects']['skip_this_round'] = False
    
    gs['current_round'] += 1
    
    if gs['current_round'] > gs['total_rounds']:
        return jsonify({'success': True, 'game_over': True})
    
    gs['round_in_progress'] = True
    gs['game_effects']['game_phase'] = 'choose_door'
    
    gs['current_round_info'] = {
        'round': gs['current_round'],
        'start_crystals': gs['crystals'],
        'start_candies': gs['candies'],
        'card': gs['deck'][0] if gs['deck'] else None,
        'question_word': None,
        'word_slots': [],
        'door_selection': None,
        'result': None,
    }
    
    refresh_word_slots(gs)
    
    return jsonify({
        'success': True,
        'round': gs['current_round'],
        'total_rounds': gs['total_rounds'],
        'crystals': gs['crystals'],
        'candies': gs['candies'],
        'unknown_cards': gs['unknown_cards'],
        'deck_count': len(gs['deck']),
        'word_slots': gs['word_slots'],
        'hand_cards': get_hand_state(gs),
        'game_phase': gs['game_effects']['game_phase'],
        'demon_lord_active': gs['game_effects'].get('demon_lord_active_this_round', False),
        'yuboyan_active': gs['game_effects'].get('yuboyan_activated', False),
        'disable_spell': gs['game_effects'].get('disable_spell_this_round', False),
    })


# ============ 游戏结束 ============

@halloween_bp.route('/api/halloween/end_game', methods=['POST'])
def end_game():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es or not es.get('game_state'):
        return jsonify({'success': False, 'message': '游戏未初始化'})
    
    gs = es['game_state']
    
    basic_score = es.get('basic_score', 0)
    vocab_deduction = gs['game_effects'].get('vocab_score_deduction', 0)
    vocab_bonus = gs['game_effects'].get('vocab_score_bonus', 0)
    evelyn_triggered = gs['game_effects'].get('evelyn_failed_proof', False)
    
    weighted_score = max(0, min(30, basic_score - vocab_deduction + vocab_bonus))
    candy_score = gs['candies']
    game_score = max(0, candy_score - 10)
    total_score = weighted_score + game_score
    is_passed = total_score >= PASS_SCORE
    
    door_counts = {'开门': 0, '不开门': 0, '跳过': 0}
    result_counts = {'正确': 0, '错误': 0, '跳过': 0}
    
    for record in gs['game_records']:
        sel = record.get('door_selection', '')
        if '开门' in sel:
            door_counts['开门'] += 1
        elif '不开门' in sel:
            door_counts['不开门'] += 1
        else:
            door_counts['跳过'] += 1
        
        res = record.get('result', '')
        if res in result_counts:
            result_counts[res] += 1
    
    es['phase'] = 'result'
    
    return jsonify({
        'success': True,
        'basic_score': basic_score,
        'weighted_score': weighted_score,
        'game_score': game_score,
        'total_score': total_score,
        'is_passed': is_passed,
        'candies': candy_score,
        'crystals': gs['crystals'],
        'unknown_cards': gs['unknown_cards'],
        'vocab_deduction': vocab_deduction,
        'vocab_bonus': vocab_bonus,
        'evelyn_triggered': evelyn_triggered,
        'spell_destroyed': gs['game_effects'].get('spell_destroyed_count', 0),
        'door_counts': door_counts,
        'result_counts': result_counts,
        'total_rounds_completed': len(gs['game_records']),
        'pass_score': PASS_SCORE,
        'full_score': FULL_SCORE,
    })


@halloween_bp.route('/api/halloween/final_report', methods=['POST'])
def final_report():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    
    gs = es.get('game_state', {})
    
    basic_score = es.get('basic_score', 0)
    vocab_deduction = gs.get('game_effects', {}).get('vocab_score_deduction', 0)
    vocab_bonus = gs.get('game_effects', {}).get('vocab_score_bonus', 0)
    weighted_score = max(0, min(30, basic_score - vocab_deduction + vocab_bonus))
    
    candy_score = gs.get('candies', 0)
    game_score = max(0, candy_score - 10)
    total_score = weighted_score + game_score
    is_passed = total_score >= PASS_SCORE
    
    game_records_detail = []
    for record in gs.get('game_records', []):
        game_records_detail.append({
            'round': record.get('round', 0),
            'start_crystals': record.get('start_crystals', 0),
            'start_candies': record.get('start_candies', 0),
            'card': record.get('card', '-'),
            'question_word': record.get('question_word', {}).get('word', '-') if record.get('question_word') else '-',
            'word_slots': record.get('word_slots', []),
            'door_selection': record.get('door_selection', '-'),
            'result': record.get('result', '-'),
            'end_crystals': record.get('end_crystals', 0),
            'end_candies': record.get('end_candies', 0),
        })
    
    return jsonify({
        'success': True,
        'basic_score': basic_score,
        'weighted_score': weighted_score,
        'game_score': game_score,
        'total_score': total_score,
        'is_passed': is_passed,
        'candies': candy_score,
        'crystals': gs.get('crystals', 0),
        'unknown_cards': gs.get('unknown_cards', 0),
        'vocab_deduction': vocab_deduction,
        'vocab_bonus': vocab_bonus,
        'evelyn_triggered': gs.get('game_effects', {}).get('evelyn_failed_proof', False),
        'spell_destroyed': gs.get('game_effects', {}).get('spell_destroyed_count', 0),
        'game_records_detail': game_records_detail,
        'basic_results': es.get('basic_results', []),
        'today_group': es.get('today', ''),
        'total_rounds': len(gs.get('game_records', [])),
    })


@halloween_bp.route('/api/halloween/get_state', methods=['POST'])
def get_state():
    """获取当前游戏状态（用于页面刷新恢复）"""
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es or not es.get('game_state'):
        return jsonify({'success': False, 'message': '游戏未初始化'})
    
    gs = es['game_state']
    
    return jsonify({
        'success': True,
        'round': gs['current_round'],
        'crystals': gs['crystals'],
        'candies': gs['candies'],
        'unknown_cards': gs['unknown_cards'],
        'word_slots': gs.get('word_slots', []),
        'hand_cards': get_hand_state(gs),
        'game_phase': gs['game_effects']['game_phase'],
        'demon_lord_active': gs['game_effects'].get('demon_lord_active_this_round', False),
        'yuboyan_active': gs['game_effects'].get('yuboyan_activated', False),
        'disable_spell': gs['game_effects'].get('disable_spell_this_round', False),
    })
# 在 halloween_web.py 中添加这个路由

@halloween_bp.route('/api/halloween/get_full_state', methods=['POST'])
def get_full_state():
    """获取完整游戏状态（用于页面初始化）"""
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es or not es.get('game_state'):
        return jsonify({'success': False, 'message': '游戏未初始化'})
    
    gs = es['game_state']
    
    return jsonify({
        'success': True,
        'game_state': {
            'current_round': gs['current_round'],
            'total_rounds': gs['total_rounds'],
            'crystals': gs['crystals'],
            'candies': gs['candies'],
            'unknown_cards': gs['unknown_cards'],
            'deck_count': len(gs['deck']),
            'game_phase': gs['game_effects']['game_phase'],
            'game_effects': gs['game_effects'],
            'hand_spell_cards': gs['hand_spell_cards'],
            'unknown_card_states': gs['unknown_card_states'],
            'word_slots': gs.get('word_slots', []),
        }
    })