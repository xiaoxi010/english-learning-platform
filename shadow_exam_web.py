# shadow_exam_web.py - 诡影重重网页版（完整修复版，含地名抽取）
from flask import Blueprint, render_template, request, jsonify
from exam_base_web import prepare_basic_words, get_all_group_names, calculate_similarity
from vocabulary_manager import get_vocab_manager
import random, re, os, uuid
from settings_web import get_all_settings

shadow_bp = Blueprint('shadow', __name__)

PASS_SCORE = 45
FULL_SCORE = 50
BASIC_FULL = 30
SHADOW_FULL = 20
PATTERN_NAME = '诡影重重'

exam_sessions = {}

# 地名、词性、权重
PLACE_CONFIG = [
    ('牡丹镇', 'n.', 2),
    ('风信坞', 'v.', 2),
    ('茉莉城', 'adj.', 2),
    ('铃兰乡', 'adv.', 2),
    ('星屿居', 'other', 1)
]

PLACE_NAMES = [p[0] for p in PLACE_CONFIG]
PLACE_WEIGHTS = [p[2] for p in PLACE_CONFIG]
POS_MAP = {p[0]: p[1] for p in PLACE_CONFIG}


@shadow_bp.route('/exam/shadow')
def shadow_page():
    settings = get_all_settings()
    return render_template('shadow_exam.html',
                         groups=get_all_group_names(),
                         pattern_name=PATTERN_NAME,
                         pass_score=PASS_SCORE,
                         full_score=FULL_SCORE,
                         basic_full=BASIC_FULL,
                         shadow_full=SHADOW_FULL,
                         place_names=PLACE_NAMES,
                         user_name=settings.get('user_name', ''),
                         student_id=settings.get('student_id', ''))


def prepare_shadow_words(today, yesterday, selected_place):
    """准备诡影重重单词 - 按指定词性和长度分类"""
    target_pos = POS_MAP.get(selected_place)
    if not target_pos:
        return None, None, '无效的地名'

    # 收集所有非今日昨日的单词
    all_groups = get_vocab_manager().get_all_groups()
    all_words = []
    for g in all_groups:
        if g['group_name'] in [today, yesterday]:
            continue
        gdata = get_vocab_manager().get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            for w in gdata['words']:
                all_words.append({
                    'word': w['word'],
                    'part_of_speech': w.get('part_of_speech', ''),
                    'chinese_meaning': w.get('chinese_meaning', '')
                })

    # 筛选包含目标词性的单词
    def has_target_pos(pos_str, target):
        if not pos_str:
            return False
        pos_list = [p.strip().lower() for p in pos_str.replace('，', ',').replace('.', ',').replace('/', ',').split(',') if p.strip()]
        if target == 'other':
            main_pos = {'n', 'v', 'adj', 'adv'}
            return not pos_list or any(p not in main_pos for p in pos_list)
        else:
            target_clean = target.replace('.', '').strip().lower()
            return target_clean in pos_list

    matched_words = [w for w in all_words if has_target_pos(w['part_of_speech'], target_pos)]

    if len(matched_words) < 30:
        return None, None, f'候选单词不足（{selected_place}词性只有{len(matched_words)}个）'

    # 按长度分类
    short_words = [w for w in matched_words if len(w['word']) <= 6]
    mid_words = [w for w in matched_words if 7 <= len(w['word']) <= 10]
    long_words = [w for w in matched_words if len(w['word']) >= 11]

    def pick_words(word_list, count):
        available = list(word_list)
        random.shuffle(available)
        selected = []
        selected_char_sets = []
        filter_chars = {'的', '地', '了'}

        for w in available:
            chars = set(re.findall(r'[\u4e00-\u9fff]', w['chinese_meaning']))
            chars = chars - filter_chars
            ok = True
            for cs in selected_char_sets:
                if len(chars & cs) >= 2:
                    ok = False
                    break
            if ok:
                selected.append(w)
                selected_char_sets.append(chars)
            if len(selected) >= count:
                break
        return selected

    short_picked = pick_words(short_words, 10)
    mid_picked = pick_words(mid_words, 10)
    long_picked = pick_words(long_words, 10)

    if len(short_picked) < 10:
        return None, None, f'短单词不足（{selected_place}词性只找到{len(short_picked)}个）'
    if len(mid_picked) < 10:
        return None, None, f'中单词不足（{selected_place}词性只找到{len(mid_picked)}个）'
    if len(long_picked) < 10:
        return None, None, f'长单词不足（{selected_place}词性只找到{len(long_picked)}个）'

    final_words = short_picked + mid_picked + long_picked
    random.shuffle(final_words)

    result = [{'word': w['word'], 'pos': w['part_of_speech'], 'meaning': w['chinese_meaning']} for w in final_words]
    return result, selected_place, None


def calc_shadow_score(ua, ca):
    if not ua:
        return 0.0
    sim = calculate_similarity(ua, ca)
    return 1.0 if sim >= 2 else (0.75 if sim == 1 else 0.0)


# ==================== API ====================

@shadow_bp.route('/api/shadow/start', methods=['POST'])
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
        'shadow': None,
        'today': today, 'yesterday': yesterday,
        'selected_place': None
    }

    return jsonify({
        'success': True, 'exam_id': exam_id,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(basic_words)],
        'total': len(basic_words)
    })


@shadow_bp.route('/api/shadow/draw_place', methods=['POST'])
def draw_place():
    """抽取地名 - 前端动画，后端实际随机抽取"""
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})

    selected_place = random.choices(PLACE_NAMES, weights=PLACE_WEIGHTS, k=1)[0]
    es['selected_place'] = selected_place

    return jsonify({
        'success': True,
        'place': selected_place
    })


@shadow_bp.route('/api/shadow/prepare_words', methods=['POST'])
def prepare_words():
    """根据抽取的地名准备单词"""
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})

    selected_place = es.get('selected_place')
    if not selected_place:
        return jsonify({'success': False, 'message': '请先抽取地名'})

    shadow_words, place, error = prepare_shadow_words(es['today'], es['yesterday'], selected_place)
    if error:
        return jsonify({'success': False, 'message': error})

    es['shadow'] = shadow_words

    return jsonify({
        'success': True,
        'place': place,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(shadow_words)],
        'total': len(shadow_words)
    })



# ========== 诡影重重 submit_basic ==========
@shadow_bp.route('/api/shadow/submit_basic', methods=['POST'])
def submit_basic():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
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
        results.append({'index': i, 'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning'],
                       'user_answer': ua, 'is_correct': ok,
                       'auto_status': 'correct' if sim >= 2 else ('wrong' if sim == 0 else 'uncertain')})
    es['basic_results'] = results
    es['basic_score'] = correct
    return jsonify({'success': True, 'results': results, 'score': correct, 'total': len(words)})


# ========== 诡影重重 start_shadow ==========
@shadow_bp.route('/api/shadow/start_shadow', methods=['POST'])
def start_shadow():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})

    corrections = data.get('corrections', {})
    if corrections:
        correct = 0
        for i, r in enumerate(es.get('basic_results', [])):
            if str(i) in corrections:
                r['is_correct'] = corrections[str(i)]
                r['score'] = '1.00' if corrections[str(i)] else '0.00'
            if r['is_correct']:
                correct += 1
        es['basic_score'] = correct

    return jsonify({'success': True,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(es['shadow'])],
        'total': len(es['shadow']), 'basic_score': es.get('basic_score', 0),
        'selected_place': es.get('selected_place', '')})


# ========== 诡影重重 submit_shadow ==========
@shadow_bp.route('/api/shadow/submit_shadow', methods=['POST'])
def submit_shadow():
    data = request.get_json()
    exam_id = data.get('exam_id', '')
    es = exam_sessions.get(exam_id)
    if not es:
        return jsonify({'success': False, 'message': '数据过期'})

    corrections = data.get('corrections', {})
    if corrections:
        for i, r in enumerate(es.get('basic_results', [])):
            if str(i) in corrections:
                r['is_correct'] = corrections[str(i)]
                r['score'] = '1.00' if corrections[str(i)] else '0.00'

    basic_results = es.get('basic_results', [])
    basic_score = sum(1 for r in basic_results if r.get('is_correct', False))

    answers = data.get('answers', {})
    results, total = [], 0.0
    for i, w in enumerate(es['shadow']):
        ua = answers.get(str(i), '').strip()
        sc = calc_shadow_score(ua, w['meaning'])
        total += sc
        results.append({'index': i, 'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning'],
                       'user_answer': ua, 'score': sc, 'score_display': f"{sc:.2f}"})

    final_shadow = min(total, 20.0)
    total_score = basic_score + final_shadow
    is_passed = total_score >= PASS_SCORE

    for r in basic_results:
        try:
            if r.get('is_correct', False):
                get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass

    for r in results:
        try:
            if r['score'] >= 1.0:
                get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass

    return jsonify({'success': True, 'results': results,
        'basic_results': basic_results,
        'shadow_score': final_shadow, 'basic_score': basic_score,
        'total_score': total_score, 'is_passed': is_passed,
        'today_group': es['today'], 'yesterday_group': es['yesterday'],
        'selected_place': es.get('selected_place', '')})


@shadow_bp.route('/api/shadow/export_png', methods=['POST'])
def export_png():
    data = request.get_json()
    try:
        from PIL import Image, ImageDraw, ImageFont
        import tempfile, base64
        from datetime import datetime

        results = data.get('results', [])
        basic_results = data.get('basic_results', [])
        total_score = float(data.get('total_score', 0))
        shadow_score = float(data.get('shadow_score', 0))
        basic_score = float(data.get('basic_score', 0))
        is_passed = bool(data.get('is_passed', False))
        today_group = data.get('today_group', '')
        user_name = data.get('user_name', '')
        student_id = data.get('student_id', '')
        yesterday_group = data.get('yesterday_group', '')
        selected_place = data.get('selected_place', '')

        S = 5
        W, H = 1290 * S, 1000 * S
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

        title = "诡影重重考试总成绩报告"
        d.text((W // 2, s(20)), title, fill=(255, 215, 0), font=ft, anchor="ma")

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
        d.text((ix + s(42), iy), "诡影重重", fill=(255, 255, 255), font=fi)
        d.text((ix + s(120), iy), "地点：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(155), iy), selected_place, fill=(255, 215, 0), font=fi)
        iy += s(18)
        bc = (46, 204, 113) if basic_score >= 18 else (231, 76, 96)
        sc = (46, 204, 113) if shadow_score >= 15 else (231, 76, 96)
        tc = (46, 204, 113) if is_passed else (231, 76, 96)
        d.text((ix, iy), f"基础词汇：{basic_score:.2f}/30", fill=bc, font=fh)
        d.text((ix + s(120), iy), f"诡影重重：{shadow_score:.2f}/20", fill=sc, font=fh)
        iy += s(18)
        d.text((ix, iy), f"总得分：{total_score:.2f}/50", fill=tc, font=fh)
        d.text((ix + s(120), iy), f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(149, 165, 166), font=ftm)
        d.text((ix + s(120), iy + s(12)), "通过标准：45分", fill=(255, 215, 0), font=ftm)

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
        for group in range(3):
            for ci, (hdr, cw) in enumerate(zip(headers4, cols4)):
                bg = (255, 215, 0) if ci == 0 else ((52, 152, 219) if ci == 1 else (42, 42, 58))
                d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm")
                hx += cw
            hx += gap

        all_words = []
        for r in basic_results:
            score_val = "1.00" if r.get('is_correct') else "0.00"
            cl = (46, 204, 113) if r.get('is_correct') else (231, 76, 96)
            all_words.append({'word': r['word'], 'pos': r.get('pos', ''), 'meaning': r['meaning'], 'score': score_val, 'color': cl})
        while len(all_words) < 30:
            all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
        for r in results:
            score_val = r.get('score_display', '0.00')
            cl = (46, 204, 113) if r.get('score', 0) >= 1 else ((255, 215, 0) if r.get('score', 0) >= 0.75 else (231, 76, 96))
            all_words.append({'word': r['word'], 'pos': r.get('pos', ''), 'meaning': r['meaning'], 'score': score_val, 'color': cl})
        while len(all_words) < 60:
            all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})

        ry = ty + s(25)
        rh = s(22)
        for row in range(20):
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
        fp = os.path.join(tmp, 'shadow_report.png')
        img.save(fp, dpi=(800, 800))
        with open(fp, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        os.remove(fp)
        return jsonify({'success': True, 'image': b64})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})