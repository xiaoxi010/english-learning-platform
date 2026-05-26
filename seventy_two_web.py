# seventy_two_web.py - 七十二变网页版（完整修复版，得分用小数，版型含词性）
from flask import Blueprint, render_template, request, jsonify
from exam_base_web import prepare_basic_words, get_all_group_names, calculate_similarity
from vocabulary_manager import VocabularyManager
import random, re, os, uuid, difflib
from settings_web import get_all_settings
seventy_two_bp = Blueprint('seventy_two', __name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocabulary.db")
vm = VocabularyManager(db_path=DB_PATH)

PASS_SCORE = 47
FULL_SCORE = 50
BASIC_FULL = 30
STRATEGY_FULL = 20
PATTERN_NAME = '七十二变'

exam_sessions = {}

# ==================== 同义缀组定义（可手动修改） ====================
AFFIX_GROUPS = [
    ['-tion'],
    ['-ssion'],
    ['-ment'],
    ['-ness'],
    ['-ity'],
    ['-ance'],
    ['-ence'],
    ['-ist'],
    ['-ism'],
    ['-able'],
    ['-ible'],
    ['-ive'],
    ['-ous'],
    ['-ful'],
    ['-less'],
    ['-al'],
    ['-ic'],
    ['-ly'],
    ['per-'],
    ['pro-'],
    ['pre-'],
    ['dis-'],
    ['des-'],
    ['mis-'],
    ['over-'],
    ['under-'],
    ['inter-'],
    ['trans-'],
    ['sub-'],
    ['com-'],
    ['con-'],
    ['res-'],
]


def parse_pos(pos_str):
    """解析词性字符串 'n./adj.' -> {'n', 'adj'}"""
    if not pos_str:
        return set()
    cleaned = re.sub(r'[，,/\.]+', ',', pos_str)
    return set(p.strip().lower() for p in cleaned.split(',') if p.strip())


def find_similar_word_for_distractor(word_info, candidate_pool, exclude_words):
    """
    找到一个与 word_info 词性相同的相似词
    返回相似词的汉译，如果找不到返回 None
    要求：相似词的汉译与目标汉译不能有 ≥ 2 个相同汉字
    """
    target_pos = parse_pos(word_info.get('part_of_speech', ''))
    if not target_pos:
        return None
    target_meaning = word_info.get('chinese_meaning', word_info.get('meaning', ''))
    word_lower = word_info['word'].lower()
    best_match = None
    best_score = 0
    for w in candidate_pool:
        if 'phr' in w.get('part_of_speech', '').lower():
            continue
        if w['word'].lower() in exclude_words or w['word'].lower() == word_lower:
            continue
        wpos = parse_pos(w.get('part_of_speech', ''))
        if not wpos or not (target_pos & wpos):
            continue
        if len(set(w['chinese_meaning']) & set(target_meaning)) >= 2:
            continue
        ws = difflib.SequenceMatcher(None, word_lower, w['word'].lower()).ratio()
        if ws > best_score:
            best_score = ws
            best_match = w
    return best_match['chinese_meaning'] if best_match else None


@seventy_two_bp.route('/exam/seventy_two')
def seventy_two_page():
    settings = get_all_settings()
    return render_template('seventy_two.html',
                         groups=get_all_group_names(),
                         pattern_name=PATTERN_NAME,
                         pass_score=PASS_SCORE,
                         full_score=FULL_SCORE,
                         basic_full=BASIC_FULL,
                         strategy_full=STRATEGY_FULL,
                         user_name=settings.get('user_name', ''),
                         student_id=settings.get('student_id', ''))


def prepare_strategy_words(today, yesterday):
    all_words = []
    for g in vm.get_all_groups():
        gdata = vm.get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            for w in gdata['words']:
                if 'phr' in w.get('part_of_speech', '').lower():
                    continue
                all_words.append({
                    'word': w['word'],
                    'chinese_meaning': w.get('chinese_meaning', ''),
                    'part_of_speech': w.get('part_of_speech', '')
                })
    if len(all_words) < 30:
        return None, None, None, None, '词汇不足'

    sample_size = max(30, int(len(all_words) * 0.75))
    candidate_pool = random.sample(all_words, sample_size)

    # ========== 1. 同缀词选择 ==========
    random.shuffle(AFFIX_GROUPS)
    suffix_words = None
    suffix_extra_meanings = []
    suffix_exclude_words = set()

    for affix_group in AFFIX_GROUPS:
        candidates = []
        for w in candidate_pool:
            word = w['word'].lower()
            matched = False
            for affix in affix_group:
                if affix.startswith('-') and word.endswith(affix[1:]):
                    matched = True
                    break
                elif affix.endswith('-') and word.startswith(affix[:-1]):
                    matched = True
                    break
            if matched:
                candidates.append({
                    'word': w['word'],
                    'meaning': w['chinese_meaning'],
                    'part_of_speech': w.get('part_of_speech', ''),
                    'full_info': w
                })

        if len(candidates) >= 12:
            filtered = [candidates[0]]
            for c in candidates[1:]:
                ok = True
                for f in filtered:
                    if difflib.SequenceMatcher(None, c['meaning'], f['meaning']).ratio() >= 0.3 or len(set(c['meaning']) & set(f['meaning'])) >= 2:
                        ok = False
                        break
                if ok:
                    filtered.append(c)
                if len(filtered) >= 12:
                    break

            if len(filtered) >= 12:
                random.shuffle(filtered)
                selected_12 = filtered[:12]
                suffix_words = selected_12[:10]
                suffix_extra = selected_12[10:12]
                suffix_extra_meanings = [w['meaning'] for w in suffix_extra]
                for i, sw in enumerate(suffix_words):
                    sw['id'] = f'suffix_{i}'
                for w in selected_12:
                    suffix_exclude_words.add(w['word'].lower())
                break

        elif len(candidates) >= 10:
            filtered = [candidates[0]]
            for c in candidates[1:]:
                ok = True
                for f in filtered:
                    if difflib.SequenceMatcher(None, c['meaning'], f['meaning']).ratio() >= 0.3 or len(set(c['meaning']) & set(f['meaning'])) >= 2:
                        ok = False
                        break
                if ok:
                    filtered.append(c)
                if len(filtered) >= 12:
                    break

            if len(filtered) >= 10:
                random.shuffle(filtered)
                suffix_words = filtered[:10]
                for i, sw in enumerate(suffix_words):
                    sw['id'] = f'suffix_{i}'
                for w in filtered:
                    suffix_exclude_words.add(w['word'].lower())

                remaining_pool = [w for w in candidate_pool if w['word'].lower() not in suffix_exclude_words]
                if len(remaining_pool) >= 2:
                    random_2 = random.sample(remaining_pool, 2)
                    for rw in random_2:
                        distractor = find_similar_word_for_distractor(rw, candidate_pool, suffix_exclude_words)
                        if distractor:
                            suffix_extra_meanings.append(distractor)
                        else:
                            remaining2 = [w for w in candidate_pool
                                          if w['word'].lower() not in suffix_exclude_words
                                          and w['chinese_meaning'] not in suffix_extra_meanings
                                          and w['chinese_meaning'] not in [sw['meaning'] for sw in suffix_words]]
                            if remaining2:
                                suffix_extra_meanings.append(random.choice(remaining2)['chinese_meaning'])
                break

    if not suffix_words:
        return None, None, None, None, '同缀词不足'

    # ========== 2. 相似词对选择 ==========
    similar_exclude_words = suffix_exclude_words.copy()

    similar_pairs = []
    pool_size = len(candidate_pool)
    for i in range(pool_size):
        for j in range(i+1, pool_size):
            w1, w2 = candidate_pool[i], candidate_pool[j]
            if w1['word'].lower() in similar_exclude_words or w2['word'].lower() in similar_exclude_words:
                continue
            if w1['word'].lower() == w2['word'].lower():
                continue
            ws = difflib.SequenceMatcher(None, w1['word'].lower(), w2['word'].lower()).ratio()
            if ws >= 0.74:
                pos1 = parse_pos(w1.get('part_of_speech', ''))
                pos2 = parse_pos(w2.get('part_of_speech', ''))
                if pos1 and pos2 and pos1 & pos2:
                    ms = difflib.SequenceMatcher(None, w1['chinese_meaning'], w2['chinese_meaning']).ratio()
                    if ms <= 0.4:
                        if len(set(w1['chinese_meaning']) & set(w2['chinese_meaning'])) < 2:
                            similar_pairs.append((w1, w2))

    if len(similar_pairs) < 5:
        return suffix_words, None, suffix_extra_meanings, None, '相似词对不足'

    random.shuffle(similar_pairs)
    similar_words = []
    similar_exclude_set = similar_exclude_words.copy()
    for w1, w2 in similar_pairs:
        if w1['word'].lower() in similar_exclude_set or w2['word'].lower() in similar_exclude_set:
            continue
        similar_exclude_set.add(w1['word'].lower())
        similar_exclude_set.add(w2['word'].lower())
        pid = len(similar_words) // 2
        similar_words.append({
            'id': f'similar_{pid}_1',
            'word': w1['word'],
            'meaning': w1['chinese_meaning'],
            'part_of_speech': w1.get('part_of_speech', ''),
            'pair_id': pid
        })
        similar_words.append({
            'id': f'similar_{pid}_2',
            'word': w2['word'],
            'meaning': w2['chinese_meaning'],
            'part_of_speech': w2.get('part_of_speech', ''),
            'pair_id': pid
        })
        if len(similar_words) >= 10:
            break

    if len(similar_words) < 10:
        return suffix_words, None, suffix_extra_meanings, None, '相似词对不足'

    # 相似词误导项：排除22个词
    similar_extra_meanings = []
    all_exclude = similar_exclude_set | set(w['word'].lower() for w in similar_words)
    remaining_pool = [w for w in candidate_pool if w['word'].lower() not in all_exclude]
    if len(remaining_pool) >= 2:
        random_2 = random.sample(remaining_pool, 2)
        for rw in random_2:
            distractor = find_similar_word_for_distractor(rw, candidate_pool, all_exclude)
            if distractor:
                similar_extra_meanings.append(distractor)
            else:
                remaining2 = [w for w in candidate_pool
                              if w['word'].lower() not in all_exclude
                              and w['chinese_meaning'] not in similar_extra_meanings
                              and w['chinese_meaning'] not in [sw['meaning'] for sw in similar_words]]
                if remaining2:
                    similar_extra_meanings.append(random.choice(remaining2)['chinese_meaning'])

    return suffix_words, similar_words, suffix_extra_meanings, similar_extra_meanings, None


def build_meaning_options(words_list, extra_meanings):
    """构建汉译选项：正确释义 + 额外误导项，不够再从全词库补"""
    correct_meanings = [w['meaning'] for w in words_list]
    all_meanings = correct_meanings.copy()

    if extra_meanings:
        for m in extra_meanings:
            if m not in all_meanings:
                all_meanings.append(m)

    if len(all_meanings) < 12:
        all_vocab = []
        for g in vm.get_all_groups():
            gdata = vm.get_word_group(g['group_name'], g.get('dict_name', ''))
            if gdata and 'words' in gdata:
                for w in gdata['words']:
                    all_vocab.append(w.get('chinese_meaning', ''))
        random.shuffle(all_vocab)
        for m in all_vocab:
            if m not in all_meanings:
                all_meanings.append(m)
                if len(all_meanings) >= 12:
                    break

    random.shuffle(all_meanings)
    return [{'text': m, 'is_correct': m in correct_meanings} for m in all_meanings]


# ==================== API ====================

@seventy_two_bp.route('/api/seventy_two/start', methods=['POST'])
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
        'suffix_words': None,
        'similar_words': None,
        'suffix_meanings': None,
        'similar_meanings': None,
        'today': today,
        'yesterday': yesterday,
        'strategy_ready': False
    }
    return jsonify({
        'success': True,
        'exam_id': exam_id,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(basic_words)],
        'total': len(basic_words)
    })


@seventy_two_bp.route('/api/seventy_two/prepare_strategy', methods=['POST'])
def prepare_strategy():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    today = es['today']
    yesterday = es['yesterday']
    suffix_words, similar_words, suffix_extra, similar_extra, error = prepare_strategy_words(today, yesterday)
    if error:
        return jsonify({'success': False, 'message': error})
    suffix_meanings = build_meaning_options(suffix_words, suffix_extra or [])
    similar_meanings = build_meaning_options(similar_words, similar_extra or [])
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
        'similar_meanings': similar_meanings
    })


@seventy_two_bp.route('/api/seventy_two/submit_basic', methods=['POST'])
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
            'index': i,
            'word': w['word'],
            'pos': w['pos'],
            'meaning': w['meaning'],
            'user_answer': ua,
            'is_correct': ok,
            'score': '1.00' if ok else '0.00',
            'auto_status': 'correct' if sim >= 2 else ('wrong' if sim == 0 else 'uncertain')
        })
    es['basic_results'] = results
    es['basic_score'] = correct
    for r in results:
        try:
            if r['is_correct']:
                vm.remove_word_from_wrong_book(r['word'])
            else:
                vm.add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass
    return jsonify({'success': True, 'results': results, 'score': correct, 'total': len(words)})


@seventy_two_bp.route('/api/seventy_two/start_strategy', methods=['POST'])
def start_strategy():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    if not es.get('strategy_ready'):
        return jsonify({'success': False, 'message': '策略词汇尚未准备完成'})
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
                vm.remove_word_from_wrong_book(r['word'])
            else:
                vm.add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass
    es['basic_score'] = correct
    return jsonify({
        'success': True,
        'suffix_words': es['suffix_words'],
        'similar_words': es['similar_words'],
        'suffix_meanings': es['suffix_meanings'],
        'similar_meanings': es['similar_meanings'],
        'basic_score': correct
    })


@seventy_two_bp.route('/api/seventy_two/submit_strategy', methods=['POST'])
def submit_strategy():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})
    pairs = data.get('pairs', {})
    all_words = es['suffix_words'] + es['similar_words']
    results, strategy_score = [], 0
    for w in all_words:
        user_meaning = pairs.get(w['id'], '')
        is_correct = user_meaning == w['meaning']
        if is_correct:
            strategy_score += 1
        results.append({
            'id': w['id'],
            'word': w['word'],
            'pos': w.get('part_of_speech', ''),
            'meaning': w['meaning'],
            'user_meaning': user_meaning,
            'is_correct': is_correct,
            'score': '1.00' if is_correct else '0.00'
        })
    basic_score = es.get('basic_score', 0)
    total_score = basic_score + strategy_score
    is_passed = total_score >= PASS_SCORE
    for r in results:
        try:
            w = next((x for x in all_words if x['id'] == r['id']), None)
            pos = w.get('part_of_speech', '') if w else ''
            if r['is_correct']:
                vm.remove_word_from_wrong_book(r['word'])
            else:
                vm.add_word_to_wrong_book(r['word'], pos, r['meaning'])
        except:
            pass
    return jsonify({
        'success': True,
        'results': results,
        'strategy_score': strategy_score,
        'basic_score': basic_score,
        'total_score': total_score,
        'is_passed': is_passed,
        'today_group': es['today'],
        'yesterday_group': es['yesterday'],
        'basic_results': es.get('basic_results', [])
    })


@seventy_two_bp.route('/api/seventy_two/export_png', methods=['POST'])
def export_png():
    data = request.get_json()
    try:
        from PIL import Image, ImageDraw, ImageFont
        import tempfile, base64
        from datetime import datetime
        basic_results = data.get('basic_results', [])
        strategy_results = data.get('strategy_results', [])
        total_score = float(data.get('total_score', 0))
        strategy_score = float(data.get('strategy_score', 0))
        basic_score = float(data.get('basic_score', 0))
        is_passed = bool(data.get('is_passed', False))
        today_group = data.get('today_group', '')
        user_name = data.get('user_name', '')
        student_id = data.get('student_id', '')
        yesterday_group = data.get('yesterday_group', '')
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

        def s(v):
            return int(v * S)

        d.text((W // 2, s(20)), "七十二变考试总成绩报告", fill=(255, 107, 53), font=ft, anchor="ma")
        top_y = s(55)
        left_x = s(40)
        left_w = (W - s(80)) // 2 - s(10)
        top_h = s(110)
        d.rectangle([left_x, top_y, left_x + left_w, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
        ix, iy = left_x + s(10), top_y + s(8)
        d.text((ix, iy), "姓名：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(42), iy), user_name, fill=(255, 255, 255), font=fi)
        d.text((ix + s(130), iy), "学号：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(175), iy), student_id, fill=(255, 255, 255), font=fi)
        iy += s(18)
        d.text((ix, iy), "今日组别：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(60), iy), today_group, fill=(255, 255, 255), font=fi)
        d.text((ix + s(130), iy), "昨日组别：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(175), iy), yesterday_group, fill=(255, 255, 255), font=fi)
        iy += s(18)
        d.text((ix, iy), "版型：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(42), iy), "七十二变", fill=(255, 255, 255), font=fi)
        iy += s(18)
        bc = (46, 204, 113) if basic_score >= 18 else (231, 76, 96)
        sc = (46, 204, 113) if strategy_score >= 13 else (231, 76, 96)
        tc = (46, 204, 113) if is_passed else (231, 76, 96)
        d.text((ix, iy), f"基础词汇：{basic_score:.2f}/30", fill=bc, font=fh)
        d.text((ix + s(120), iy), f"版型分数：{strategy_score}/20", fill=sc, font=fh)
        iy += s(18)
        d.text((ix, iy), f"总得分：{total_score:.2f}/50", fill=tc, font=fh)
        d.text((ix + s(120), iy), f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(149, 165, 166), font=ftm)
        rx = left_x + left_w + s(20)
        rw = left_w
        d.rectangle([rx, top_y, rx + rw, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
        pp = r"E:\vxcode数据文件\static\images\通过.png" if is_passed else r"E:\vxcode数据文件\static\images\挂科.png"
        if os.path.exists(pp):
            pi = Image.open(pp).resize((s(140), s(85)), Image.Resampling.LANCZOS)
            img.paste(pi, (rx + (rw - s(140)) // 2, top_y + (top_h - s(85)) // 2))
        else:
            d.text((rx + rw // 2, top_y + top_h // 2), "通过" if is_passed else "挂科", fill=tc, font=fh, anchor="mm")
        ty = top_y + top_h + s(15)
        cols4 = [s(140), s(50), s(130), s(50)]
        headers4 = ["单词", "词性", "汉译", "得分"]
        gap = s(12)
        hx = s(45)
        for grp in range(3):
            for ci, (hdr, cw) in enumerate(zip(headers4, cols4)):
                bg = (255, 107, 53) if ci == 0 else ((52, 152, 219) if ci == 1 else (42, 42, 58))
                d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm")
                hx += cw
            hx += gap
        all_words = []
        ry = ty + s(25)
        rh = s(22)
        for r in basic_results:
            cl = (46, 204, 113) if r.get('is_correct') else (231, 76, 96)
            all_words.append({
                'word': r['word'],
                'pos': r.get('pos', ''),
                'meaning': r['meaning'],
                'score': r.get('score', '0.00'),
                'color': cl
            })
        while len(all_words) < 30:
            all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
        for r in strategy_results:
            cl = (46, 204, 113) if r.get('is_correct') else (231, 76, 96)
            all_words.append({
                'word': r['word'],
                'pos': r.get('pos', ''),
                'meaning': r['meaning'],
                'score': r.get('score', '0.00'),
                'color': cl
            })
        while len(all_words) < 50:
            all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
        for row in range(17):
            bg_row = (42, 42, 58) if row % 2 == 0 else (37, 37, 53)
            d.rectangle([s(40), ry, s(40) + s(35), ry + rh], fill=(26, 26, 42), outline=(255, 255, 255), width=1)
            d.text((s(40) + s(17), ry + rh // 2), f"{(row + 1):02d}", fill=(52, 152, 219), font=ftc, anchor="mm")
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
        fp = os.path.join(tmp, 'seventy_two_report.png')
        img.save(fp, dpi=(800, 800))
        with open(fp, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        os.remove(fp)
        return jsonify({'success': True, 'image': b64})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})