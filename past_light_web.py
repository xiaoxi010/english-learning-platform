# past_light_web.py - 昔日之光（对应PastLightExam）
from flask import Blueprint, render_template, request, jsonify, session
from exam_base_web import prepare_basic_words, get_all_group_names, calculate_similarity, auto_correct_single
from vocabulary_manager import get_vocab_manager
from settings_web import get_all_settings
import os

past_light_bp = Blueprint('past_light', __name__)

PASS_SCORE = 28
FULL_SCORE = 30
PATTERN_NAME = '昔日之光'


from settings_web import get_all_settings

@past_light_bp.route('/exam/past_light')
def past_light_page():
    settings = get_all_settings()
    return render_template('past_light.html',
                         groups=get_all_group_names(),
                         pattern_name='昔日之光',
                         pass_score=PASS_SCORE,
                         full_score=FULL_SCORE,
                         user_name=settings.get('user_name', ''),
                         student_id=settings.get('student_id', ''))


@past_light_bp.route('/api/past_light/start', methods=['POST'])
def start_exam():
    data = request.get_json()
    today = data.get('today_group', '').strip()
    yesterday = data.get('yesterday_group', '').strip()
    if not today or not yesterday:
        return jsonify({'success': False, 'message': '请选择今日和昨日单词组'})
    words, error = prepare_basic_words(today, yesterday)
    if error:
        return jsonify({'success': False, 'message': error})
    session['pl_words'] = words
    session['pl_today'] = today
    return jsonify({
        'success': True,
        'words': [{'word': w['word'], 'pos': w['pos'], 'index': i} for i, w in enumerate(words)],
        'total': len(words)
    })


@past_light_bp.route('/api/past_light/submit', methods=['POST'])
def submit_exam():
    data = request.get_json()
    answers = data.get('answers', {})
    corrections = data.get('corrections', {})
    words = session.get('pl_words', [])
    if not words:
        return jsonify({'success': False, 'message': '数据过期'})

    results = []
    correct_count = 0
    for i, w in enumerate(words):
        ua = answers.get(str(i), '').strip()
        is_correct, status = auto_correct_single(ua, w['meaning'])
        # 手动修正优先
        if str(i) in corrections:
            is_correct = corrections[str(i)]
        if is_correct:
            correct_count += 1
        results.append({
            'index': i, 'word': w['word'], 'pos': w['pos'],
            'meaning': w['meaning'], 'user_answer': ua,
            'is_correct': is_correct, 'auto_status': status
        })

    total_score = correct_count
    is_passed = total_score >= PASS_SCORE

    # 错题本处理（对应process_wrong_books_for_past_light）
    _process_wrong_books(results)

    return jsonify({
        'success': True, 'results': results,
        'total_score': total_score, 'is_passed': is_passed,
        'correct_count': correct_count, 'total': len(words),
        'today_group': session.get('pl_today', ''),
        'pass_score': PASS_SCORE, 'full_score': FULL_SCORE
    })
@past_light_bp.route('/api/past_light/export_png', methods=['POST'])
@past_light_bp.route('/api/past_light/export_png', methods=['POST'])
def export_png():
    data = request.get_json()
    try:
        from PIL import Image, ImageDraw, ImageFont
        import tempfile, base64
        from datetime import datetime

        results = data.get('results', [])
        total_score = float(data.get('total_score', 0))
        is_passed = bool(data.get('is_passed', False))
        today_group = data.get('today_group', '')
        user_name = data.get('user_name', '')
        student_id = data.get('student_id', '')

        S = 5
        W, H = 1290 * S, 860 * S
        img = Image.new('RGB', (W, H), (26, 26, 42))
        d = ImageDraw.Draw(img)

        try:
            ft = ImageFont.truetype("msyh.ttc", 24 * S)
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
        title = "昔日之光考试总成绩报告"
        d.text((W // 2, s(20)), title, fill=(255, 215, 0), font=ft, anchor="ma")

        # 上半
        top_y = s(55)
        left_x = s(40)
        left_w = (W - s(80)) // 2 - s(10)
        top_h = s(90)
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
        d.text((ix + s(165), iy), "昔日之光", fill=(255, 255, 255), font=fi)
        iy += s(18)
        tc = (46, 204, 113) if is_passed else (231, 76, 96)
        d.text((ix, iy), f"基础词汇：{total_score}/30", fill=tc, font=fh)
        iy += s(18)
        d.text((ix, iy), f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(149, 165, 166), font=ftm)
        d.text((ix + s(190), iy), "通过标准：28分", fill=(255, 215, 0), font=ftm)

        # 照片
        rx = left_x + left_w + s(20)
        rw = left_w
        d.rectangle([rx, top_y, rx + rw, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
        pp = r"E:\vxcode数据文件\static\images\通过.png" if is_passed else r"E:\vxcode数据文件\static\images\挂科.png"
        if os.path.exists(pp):
            pi = Image.open(pp).resize((s(140), s(75)), Image.Resampling.LANCZOS)
            img.paste(pi, (rx + (rw - s(140)) // 2, top_y + (top_h - s(75)) // 2))
        else:
            d.text((rx + rw // 2, top_y + top_h // 2), "通过" if is_passed else "挂科", fill=tc, font=fh, anchor="mm")

        # 表格 - 4列：单词/词性/汉译/得分，每行2组
        ty = top_y + top_h + s(15)
        cols4 = [s(200), s(50), s(250), s(55)]
        headers4 = ["单词", "词性", "汉译", "得分"]
        gap = s(15)

        # 表头
        hx = s(40)
        for group in range(2):
            for ci, (hdr, cw) in enumerate(zip(headers4, cols4)):
                if ci == 0: bg = (255, 215, 0)
                elif ci == 1: bg = (52, 152, 219)
                else: bg = (42, 42, 58)
                d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm")
                hx += cw
            hx += gap

        # 行
        ry = ty + s(24)
        rh = s(22)
        for row in range(15):
            for col in range(2):
                idx = row * 2 + col
                cx = s(40) + col * (sum(cols4) + gap)
                if idx < len(results):
                    r = results[idx]
                    cl = (46, 204, 113) if r.get('is_correct') else (231, 76, 96)
                    score = "1.00" if r.get('is_correct') else "0.00"
                    vals = [r['word'], r.get('pos', ''), r['meaning'], score]
                else:
                    cl = (127, 140, 141)
                    vals = ['-', '-', '-', '-']
                bg_row = (42, 42, 58) if row % 2 == 0 else (37, 37, 53)
                for ci, (cw, txt) in enumerate(zip(cols4, vals)):
                    d.rectangle([cx, ry, cx + cw, ry + rh], fill=bg_row, outline=(255, 255, 255), width=1)
                    fc = cl if (ci == 0 or ci == 3) else ((52, 152, 219) if ci == 1 else (255, 255, 255))
                    f = fe if (ci == 0 or ci == 3) else ftc
                    d.text((cx + cw // 2, ry + rh // 2), txt[:18], fill=fc, font=f, anchor="mm")
                    cx += cw
            ry += rh

        tmp = tempfile.gettempdir()
        fp = os.path.join(tmp, 'past_light_report.png')
        img.save(fp, dpi=(800, 800))
        with open(fp, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        os.remove(fp)
        return jsonify({'success': True, 'image': b64})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

def _process_wrong_books(results):
    """处理错题本"""
    for r in results:
        try:
            if r['is_correct']:
                get_vocab_manager().remove_word_from_wrong_book(r['word'])
            else:
                get_vocab_manager().add_word_to_wrong_book(r['word'], r['pos'], r['meaning'])
        except:
            pass
