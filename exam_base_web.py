# exam_base_web.py - 基础词汇共用模块（对应BaseExam）
from vocabulary_manager import get_vocab_manager
import random


def get_all_group_names():
    """获取所有单词组名称列表"""
    return [g['group_name'] for g in get_vocab_manager().get_all_groups()]


def prepare_basic_words(today_group, yesterday_group):
    """准备基础词汇：今日20+昨日10，随机打乱"""
    vm = get_vocab_manager()
    today_data, yesterday_data = None, None
    for dict_name in vm.get_active_dictionaries():
        if not today_data:
            today_data = vm.get_word_group(today_group, dict_name)
        if not yesterday_data:
            yesterday_data = vm.get_word_group(yesterday_group, dict_name)
        if today_data and yesterday_data:
            break
    if not today_data or not yesterday_data:
        return None, '单词组不存在'
    t_words, y_words = today_data['words'], yesterday_data['words']
    if len(t_words) < 20 or len(y_words) < 10:
        return None, f'单词不足（今日{len(t_words)}≥20，昨日{len(y_words)}≥10）'
    selected = random.sample(t_words, 20) + random.sample(y_words, 10)
    random.shuffle(selected)
    return [{'word': w['word'], 'pos': w.get('part_of_speech',''), 'meaning': w.get('chinese_meaning','')} for w in selected], None


def calculate_similarity(user_answer, correct_answer):
    """计算相似度（相同字符数，过滤"的""地""是"）"""
    if not user_answer or not correct_answer:
        return 0
    for ch in ['的','地','是']:
        user_answer = user_answer.replace(ch, '')
        correct_answer = correct_answer.replace(ch, '')
    if not user_answer or not correct_answer:
        return 0
    c = 0
    for char in set(user_answer):
        if char in correct_answer:
            c += min(user_answer.count(char), correct_answer.count(char))
    return c


def auto_correct_single(user_answer, correct_answer):
    """
    自动批改单个答案
    返回 (is_correct, status)
    status: 'correct'(≥2) | 'wrong'(=0或空) | 'uncertain'(=1)
    """
    if not user_answer:
        return False, 'wrong'
    sim = calculate_similarity(user_answer, correct_answer)
    if sim >= 2:
        return True, 'correct'
    elif sim == 0:
        return False, 'wrong'
    else:
        return False, 'uncertain'
