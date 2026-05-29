# thirty_six_web.py - 三十六计网页版（完整最终版）
from flask import Blueprint, render_template, request, jsonify
from exam_base_web import prepare_basic_words, get_all_group_names, calculate_similarity
from vocabulary_manager import get_vocab_manager
import random, os, uuid
from settings_web import get_all_settings
thirty_six_bp = Blueprint('thirty_six', __name__)

PASS_SCORE = 47
FULL_SCORE = 50
BASIC_FULL = 30
STRATEGY_FULL = 20
PATTERN_NAME = '三十六计'

exam_sessions = {}


@thirty_six_bp.route('/exam/thirty_six')
def thirty_six_page():
    settings = get_all_settings()
    return render_template('thirty_six.html',
                         groups=get_all_group_names(),
                         pattern_name=PATTERN_NAME,
                         pass_score=PASS_SCORE, full_score=FULL_SCORE,
                         basic_full=BASIC_FULL, strategy_full=STRATEGY_FULL,
                         user_name=settings.get('user_name', ''),
                         student_id=settings.get('student_id', ''))


def split_meanings(meaning_str):
    # 同时支持英文分号和中文分号
    meaning_str = meaning_str.replace('；', ';')
    return [m.strip() for m in meaning_str.split(';') if m.strip()]


def check_pos_match(pos1, pos2):
    p1 = [p.strip() for p in pos1.split('/') if p.strip()]
    p2 = [p.strip() for p in pos2.split('/') if p.strip()]
    if not p1 or not p2:
        return True
    return bool(set(p1) & set(p2))
def split_into_words(text):
    """将汉译字符串拆分成词语列表"""
    if ';' in text:
        return [w.strip() for w in text.split(';') if w.strip()]
    words = []
    current = ''
    for char in text:
        if char not in [' ', '，', '；', ',', ';']:
            current += char
        elif current:
            words.append(current)
            current = ''
    if current:
        words.append(current)
    return words if words else [text]


def calculate_single_meaning_similarity(meaning1, meaning2):
    """计算两个汉译之间的相似度"""
    if not meaning1 or not meaning2:
        return 0.0
    if meaning1 == meaning2:
        return 1.0
    if meaning1 in meaning2 or meaning2 in meaning1:
        return 0.9
    words1 = split_into_words(meaning1)
    words2 = split_into_words(meaning2)
    common = set(words1) & set(words2)
    if common:
        return 0.8 + len(common) * 0.1
    set1 = set(meaning1)
    set2 = set(meaning2)
    if not set1 or not set2:
        return 0.0
    inter = len(set1 & set2)
    union = len(set1 | set2)
    return inter / union if union > 0 else 0.0

def prepare_strategy_words(today, yesterday):
    all_words = []
    seen_words = set()  # 按小写单词去重
    for g in get_vocab_manager().get_all_groups():
        gdata = get_vocab_manager().get_word_group(g['group_name'], g.get('dict_name', ''))
        if gdata and 'words' in gdata:
            for w in gdata['words']:
                word_key = w['word'].lower()
                if word_key not in seen_words:
                    seen_words.add(word_key)
                    all_words.append(w)

    if len(all_words) < 100:
        return None, '词汇不足'

    basic_words, _ = prepare_basic_words(today, yesterday)
    if not basic_words:
        return None, '基础词汇不足'

    used_words = set()
    used_meanings = set()
    meanings = []

    # 构建可用种子池：先基础词汇，后词典
    basic_word_set = set(w['word'].lower() for w in basic_words)
    all_seeds = list(basic_words) + [w for w in all_words if w['word'].lower() not in basic_word_set]

    max_attempts = len(all_seeds) * 3  # 防止死循环

    while len(meanings) < 10 and max_attempts > 0:
        max_attempts -= 1

        # 从所有未使用的单词中随机抽取种子
        available_seeds = [w for w in all_seeds if w['word'].lower() not in used_words]
        if not available_seeds:
            break

        seed_word = random.choice(available_seeds)
        seed_key = seed_word['word'].lower()

        seed_pos = seed_word.get('pos', seed_word.get('part_of_speech', ''))
        seed_pos_list = [p.strip() for p in seed_pos.split('/') if p.strip()]
        if not seed_pos_list:
            used_words.add(seed_key)  # 标记为已使用，避免反复抽到
            continue

        seed_all_meanings = split_meanings(seed_word.get('meaning', seed_word.get('chinese_meaning', '')))
        if not seed_all_meanings:
            used_words.add(seed_key)
            continue

        # 过滤掉与已有组汉译相似度 >= 0.4 的汉译
        valid_meanings = []
        for m in seed_all_meanings:
            if m in used_meanings:
                continue
            too_similar = False
            for existing_m in used_meanings:
                if calculate_single_meaning_similarity(m, existing_m) >= 0.3:
                    too_similar = True
                    break
            if not too_similar:
                valid_meanings.append(m)

        if not valid_meanings:
            used_words.add(seed_key)
            continue

        # 统计每条有效汉译能找到几个匹配单词（遍历整个词典）
        meaning_matches = {}
        for m in valid_meanings:
            matches = []
            for dw in all_words:
                dw_key = dw['word'].lower()
                if dw_key in used_words or dw_key == seed_key:
                    continue
                if not check_pos_match(seed_pos, dw.get('part_of_speech', '')):
                    continue
                dw_meanings = split_meanings(dw.get('chinese_meaning', ''))
                if m in dw_meanings:
                    matches.append(dw)
            meaning_matches[m] = matches

        # 方案A：单条 ≥ 2 个
        group_words = []
        group_meanings = []

        for m, matches in meaning_matches.items():
            if len(matches) >= 2:
                group_meanings = [m]
                group_words = [seed_word, matches[0], matches[1]]
                break

        # 方案B：两条各 ≥ 1 个
        if not group_words:
            m_list = list(meaning_matches.keys())
            for i in range(len(m_list)):
                for j in range(i + 1, len(m_list)):
                    m1, m2 = m_list[i], m_list[j]
                    if len(meaning_matches[m1]) >= 1 and len(meaning_matches[m2]) >= 1:
                        match1 = meaning_matches[m1][0]
                        match2 = meaning_matches[m2][0]
                        if match1['word'].lower() != match2['word'].lower():
                            group_meanings = [m1, m2]
                            group_words = [seed_word, match1, match2]
                            break
                if group_words:
                    break

        if len(group_words) < 3:
            used_words.add(seed_key)
            continue

        # 找到一组！记录
        for sw in group_words:
            used_words.add(sw['word'].lower() if isinstance(sw, dict) else sw.lower())
        for gm in group_meanings:
            used_meanings.add(gm)

        group_word_list = []
        for w in group_words:
            if isinstance(w, dict):
                group_word_list.append({
                    'word': w.get('word', ''),
                    'part_of_speech': w.get('part_of_speech', w.get('pos', '')),
                    'chinese_meaning': w.get('chinese_meaning', w.get('meaning', '')),
                    'is_itself': (w.get('word', '').lower() == seed_key)
                })
            else:
                group_word_list.append({
                    'word': w,
                    'part_of_speech': seed_pos,
                    'chinese_meaning': seed_word.get('meaning', seed_word.get('chinese_meaning', '')),
                    'is_itself': (w.lower() == seed_key)
                })

        meanings.append({
            'meaning': ';'.join(group_meanings),
            'words': group_word_list,
            'from_basic': seed_key in basic_word_set
        })

        print(f"[调试] 第{len(meanings)}组: 种子={seed_key}, 汉译={group_meanings}, 剩余尝试={max_attempts}")

    if len(meanings) < 10:
        return None, f'只找到{len(meanings)}组（需10组）'

    # 构建卡片池
    card_pool = []
    for mi, m in enumerate(meanings):
        for wi, w in enumerate(m['words']):
            card_pool.append({
                'id': f'card_{mi}_{wi}',
                'word': w['word'],
                'pos': w.get('part_of_speech', ''),
                'meaning': w.get('chinese_meaning', ''),
                'target_meaning': m['meaning'],
                'meaning_index': mi
            })
    random.shuffle(card_pool)
    wc = {}
    for c in card_pool:
        k = c['word'].lower()
        wc[k] = wc.get(k, 0) + 1
    if any(v > 1 for v in wc.values()):
        return None, '出题出现重复单词'

    return {'meanings': meanings, 'card_pool': card_pool}, None


# ==================== 以下 API 不变 ====================

@thirty_six_bp.route('/api/thirty_six/start', methods=['POST'])
def start_exam():
    data = request.get_json()
    today = data.get('today_group', '').strip()
    yesterday = data.get('yesterday_group', '').strip()
    if not today or not yesterday:
        return jsonify({'success': False, 'message': '请选择今日和昨日单词组'})

    basic_words, error = prepare_basic_words(today, yesterday)
    if error:
        return jsonify({'success': False, 'message': error})

    strategy_data = None
    for retry in range(5):
        strategy_data, error = prepare_strategy_words(today, yesterday)
        if not error:
            break
    if error:
        return jsonify({'success': False, 'message': f'出题失败: {error}'})

    exam_id = str(uuid.uuid4())
    exam_sessions[exam_id] = {
        'basic': [{'word': w['word'], 'pos': w['pos'], 'meaning': w['meaning']} for w in basic_words],
        'meanings': strategy_data['meanings'],
        'card_pool': strategy_data['card_pool'],
        'today': today, 'yesterday': yesterday,
        'hand_cards': strategy_data['card_pool'][:7], 'pool_index': 7, 'placements': {}
    }
    return jsonify({'success': True, 'exam_id': exam_id,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(basic_words)],
        'total': len(basic_words)})


# ========== 三十六计 submit_basic ==========
@thirty_six_bp.route('/api/thirty_six/submit_basic', methods=['POST'])
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
    es['basic_results'] = results
    es['basic_score'] = correct
    return jsonify({'success': True, 'results': results, 'score': correct, 'total': len(words)})


# ========== 三十六计 start_strategy ==========
@thirty_six_bp.route('/api/thirty_six/start_strategy', methods=['POST'])
def start_strategy():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
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
        'meanings': [{'meaning': m['meaning'], 'index': i} for i, m in enumerate(es['meanings'])],
        'hand_cards': es['hand_cards'], 'placements': es['placements'],
        'pool_remaining': len(es['card_pool']) - es['pool_index'], 'basic_score': es.get('basic_score', 0)})


# ========== 三十六计 submit_strategy ==========
@thirty_six_bp.route('/api/thirty_six/submit_strategy', methods=['POST'])
def submit_strategy():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})

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
    
    area_correct = {}
    for card_id, mi in es['placements'].items():
        card_data = next((c for c in es['card_pool'] if c['id'] == card_id), None)
        if card_data and card_data['meaning_index'] == mi:
            area_correct[mi] = area_correct.get(mi, 0) + 1
    
    strategy_score = 0
    for mi in range(10):
        matches = area_correct.get(mi, 0)
        if matches >= 2:
            strategy_score += 2
        elif matches == 1:
            strategy_score += 1
    
    word_full_meaning = {}
    for w in es['basic']:
        word_full_meaning[w['word'].lower()] = w['meaning']
    for card in es['card_pool']:
        if card['word'].lower() not in word_full_meaning:
            word_full_meaning[card['word'].lower()] = card['meaning']
    
    results = []
    for card in es['card_pool']:
        card_id = card['id']
        placed_mi = es['placements'].get(card_id)
        is_correct = (placed_mi is not None and placed_mi == card['meaning_index'])
        results.append({
            'word': card['word'],
            'pos': card['pos'],
            'meaning': card['meaning'],
            'target_meaning': card['target_meaning'],
            'is_correct': is_correct,
            'score': '1.00' if is_correct else '0.00'
        })
    
    basic_results = es.get('basic_results', [])
    basic_score = sum(1 for r in basic_results if r.get('is_correct', False))
    total_score = basic_score + strategy_score
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
            full_meaning = word_full_meaning.get(r['word'].lower(), r['target_meaning'])
            if r['is_correct']:
                get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], full_meaning)
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
        'basic_results': basic_results,
        'meanings': [{'meaning': m['meaning']} for m in es['meanings']],
        'area_correct': area_correct
    })

@thirty_six_bp.route('/api/thirty_six/export_png', methods=['POST'])
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

        S = 5; W, H = 1290 * S, 950 * S
        img = Image.new('RGB', (W, H), (26, 26, 42))
        d = ImageDraw.Draw(img)
        try:
            ft = ImageFont.truetype("msyh.ttc", 20 * S); fh = ImageFont.truetype("msyh.ttc", 12 * S)
            fi = ImageFont.truetype("msyh.ttc", 10 * S); ftm = ImageFont.truetype("msyh.ttc", 9 * S)
            fth = ImageFont.truetype("msyh.ttc", 10 * S); ftc = ImageFont.truetype("msyh.ttc", 9 * S)
            fe = ImageFont.truetype("arial.ttf", 9 * S)
        except: ft=fh=fi=ftm=fth=ftc=fe=ImageFont.load_default()
        def s(v): return int(v * S)

        title = "三十六计考试总成绩报告"
        d.text((W//2, s(20)), title, fill=(255, 107, 53), font=ft, anchor="ma")

        top_y=s(55); left_x=s(40); left_w=(W-s(80))//2-s(10); top_h=s(110)
        d.rectangle([left_x,top_y,left_x+left_w,top_y+top_h],fill=(42,42,58),outline=(255,255,255),width=1)
        ix,iy=left_x+s(10),top_y+s(8)
        d.text((ix,iy),"姓名：",fill=(52,152,219),font=fh);d.text((ix+s(42),iy),user_name,fill=(255,255,255),font=fi)
        d.text((ix+s(130),iy),"学号：",fill=(52,152,219),font=fh);d.text((ix+s(175),iy),student_id,fill=(255,255,255),font=fi)
        iy+=s(18)
        d.text((ix,iy),"今日组别：",fill=(52,152,219),font=fh);d.text((ix+s(60),iy),today_group,fill=(255,255,255),font=fi)
        d.text((ix+s(130),iy),"版型：",fill=(52,152,219),font=fh);d.text((ix+s(165),iy),"三十六计",fill=(255,255,255),font=fi)
        iy+=s(18)
        bc=(46,204,113) if basic_score>=18 else (231,76,96);sc=(46,204,113) if strategy_score>=25 else (231,76,96)
        tc=(46,204,113) if is_passed else (231,76,96)
        d.text((ix,iy),f"基础词汇：{basic_score:.2f}/30",fill=bc,font=fh)
        d.text((ix+s(120),iy),f"版型分数：{strategy_score}/20",fill=sc,font=fh)
        iy+=s(18)
        d.text((ix,iy),f"总得分：{total_score:.2f}/50",fill=tc,font=fh)
        d.text((ix+s(120),iy),f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",fill=(149,165,166),font=ftm)

        rx=left_x+left_w+s(20);rw=left_w
        d.rectangle([rx,top_y,rx+rw,top_y+top_h],fill=(42,42,58),outline=(255,255,255),width=1)
        pp=r"E:\vxcode数据文件\static\images\通过.png" if is_passed else r"E:\vxcode数据文件\static\images\挂科.png"
        if os.path.exists(pp): pi=Image.open(pp).resize((s(140),s(85)),Image.Resampling.LANCZOS);img.paste(pi,(rx+(rw-s(140))//2,top_y+(top_h-s(85))//2))
        else: d.text((rx+rw//2,top_y+top_h//2),"通过" if is_passed else "挂科",fill=tc,font=fh,anchor="mm")

        ty=top_y+top_h+s(15);cols4=[s(140),s(50),s(130),s(50)];headers4=["单词","词性","汉译","得分"];gap=s(12)
        hx=s(45)
        for grp in range(3):
            for ci,(hdr,cw) in enumerate(zip(headers4,cols4)):
                bg=(255,107,53) if ci==0 else ((52,152,219) if ci==1 else (42,42,58))
                d.rectangle([hx,ty,hx+cw,ty+s(22)],fill=bg,outline=(255,255,255),width=1)
                d.text((hx+cw//2,ty+s(11)),hdr,fill=(255,255,255),font=fth,anchor="mm");hx+=cw
            hx+=gap

        all_words=[];ry=ty+s(25);rh=s(22)
        for r in basic_results:
            cl=(46,204,113) if r.get('is_correct') else (231,76,96)
            all_words.append({'word':r['word'],'pos':r.get('pos',''),'meaning':r['meaning'],'score':r.get('score','0.00'),'color':cl})
        while len(all_words)<30:all_words.append({'word':'-','pos':'-','meaning':'-','score':'0.00','color':(127,140,141)})
        for r in strategy_results:
            cl=(46,204,113) if r.get('is_correct') else (231,76,96)
            all_words.append({'word':r['word'],'pos':r.get('pos',''),'meaning':r.get('meaning',''),'score':r.get('score','0.00'),'color':cl})
        while len(all_words)<60:all_words.append({'word':'-','pos':'-','meaning':'-','score':'0.00','color':(127,140,141)})

        for row in range(20):
            bg_row=(42,42,58) if row%2==0 else (37,37,53)
            d.rectangle([s(40),ry,s(40)+s(35),ry+rh],fill=(26,26,42),outline=(255,255,255),width=1)
            d.text((s(40)+s(17),ry+rh//2),f"{(row+1):02d}",fill=(52,152,219),font=ftc,anchor="mm")
            cx_start=s(40)+s(35)
            for col in range(3):
                idx=row*3+col;cx=cx_start+col*(sum(cols4)+gap)
                if idx<len(all_words):w=all_words[idx];vals=[w['word'],w['pos'],w['meaning'],w['score']]
                else:vals=['-','-','-','-'];w={'color':(127,140,141)}
                for ci,(cw,txt) in enumerate(zip(cols4,vals)):
                    d.rectangle([cx,ry,cx+cw,ry+rh],fill=bg_row,outline=(255,255,255),width=1)
                    fc=w['color'] if ci==0 or ci==3 else ((52,152,219) if ci==1 else (255,255,255))
                    f=fe if(ci==0 or ci==3) else ftc
                    d.text((cx+cw//2,ry+rh//2),txt[:15],fill=fc,font=f,anchor="mm");cx+=cw
            ry+=rh

        tmp=tempfile.gettempdir();fp=os.path.join(tmp,'thirty_six_report.png')
        img.save(fp,dpi=(800,800))
        with open(fp,'rb') as f:b64=base64.b64encode(f.read()).decode()
        os.remove(fp)
        return jsonify({'success':True,'image':b64})
    except Exception as e:
        import traceback;traceback.print_exc()
        return jsonify({'success':False,'message':str(e)})

@thirty_six_bp.route('/api/thirty_six/place_card', methods=['POST'])
def place_card():
    data = request.get_json()
    es = exam_sessions.get(data.get('exam_id', ''))
    if not es: return jsonify({'success': False, 'message': '数据过期'})
    card_id = data.get('card_id', '')
    meaning_index = data.get('meaning_index', -1)
    if sum(1 for v in es['placements'].values() if v == meaning_index) >= 3:
        return jsonify({'success': False, 'message': '该区域已满'})
    es['placements'][card_id] = meaning_index
    es['hand_cards'] = [c for c in es['hand_cards'] if c['id'] != card_id]
    if es['pool_index'] < len(es['card_pool']):
        es['hand_cards'].append(es['card_pool'][es['pool_index']])
        es['pool_index'] += 1
    return jsonify({'success': True, 'hand_cards': es['hand_cards'], 'placements': es['placements']})


