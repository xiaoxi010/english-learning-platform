# shadow_hunter_png.py - 阴影迷踪PNG导出
from flask import Blueprint, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import tempfile, base64, os
from datetime import datetime

shadow_hunter_png_bp = Blueprint('shadow_hunter_png', __name__)

TREASURE_NAMES = ['青山', '寒山', '沧山', '暮山', '尘山']

@shadow_hunter_png_bp.route('/api/shadow_hunter/export_png', methods=['POST'])
def export_png():
    """导出阴影迷踪成绩报告PNG"""
    data = request.get_json()
    try:
        basic_results = data.get('basic_results', [])
        pattern_results = data.get('pattern_results', [])
        total_score = float(data.get('total_score', 0))
        pattern_score = float(data.get('pattern_score', 0))
        basic_score = float(data.get('basic_score', 0))
        is_passed = bool(data.get('is_passed', False))
        today_group = data.get('today_group', '')
        user_name = data.get('user_name', '')
        student_id = data.get('student_id', '')
        selected_pattern = data.get('selected_pattern', '')
        pass_score = data.get('pass_score', 46)

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

        # 标题
        title = "阴影迷踪考试总成绩报告"
        d.text((W // 2, s(20)), title, fill=(255, 107, 53), font=ft, anchor="ma")

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
        d.text((ix + s(165), iy), "阴影迷踪", fill=(255, 107, 53), font=fi)
        iy += s(18)
        d.text((ix, iy), "抽取版型：", fill=(52, 152, 219), font=fh)
        d.text((ix + s(60), iy), selected_pattern, fill=(255, 107, 53), font=fi)
        iy += s(18)
        bc = (46, 204, 113) if basic_score >= 18 else (231, 76, 96)
        sc = (46, 204, 113) if pattern_score >= 15 else (231, 76, 96)
        tc = (46, 204, 113) if is_passed else (231, 76, 96)
        d.text((ix, iy), f"基础词汇：{basic_score:.2f}/30", fill=bc, font=fh)
        d.text((ix + s(120), iy), f"{selected_pattern}：{pattern_score:.2f}/20", fill=sc, font=fh)
        iy += s(18)
        d.text((ix, iy), f"总得分：{total_score:.2f}/50", fill=tc, font=fh)
        d.text((ix + s(120), iy), f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(149, 165, 166), font=ftm)
        d.text((ix + s(120), iy + s(12)), f"通过标准：{pass_score}分", fill=(255, 215, 0), font=ftm)

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
                bg = (255, 107, 53) if ci == 0 else ((52, 152, 219) if ci == 1 else (42, 42, 58))
                d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm")
                hx += cw
            hx += gap

        # 准备单词数据
        all_words = []
        for r in basic_results:
            score_val = r.get('score_display', r.get('score', '0.00'))
            try:
                sv = float(score_val)
                cl = (46, 204, 113) if sv >= 0.99 else ((255, 215, 0) if sv >= 0.5 else (231, 76, 96))
            except:
                cl = (127, 140, 141)
            all_words.append({'word': r['word'], 'pos': r.get('pos', ''), 'meaning': r['meaning'], 'score': str(score_val), 'color': cl})
        while len(all_words) < 30:
            all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
        
        for r in pattern_results:
            score_val = r.get('score_display', r.get('score', '1.00' if r.get('is_correct') else '0.00'))
            try:
                sv = float(score_val)
                cl = (46, 204, 113) if sv >= 0.99 else ((255, 215, 0) if sv >= 0.5 else (231, 76, 96))
            except:
                cl = (46, 204, 113) if r.get('is_correct') else (231, 76, 96)
            all_words.append({'word': r['word'], 'pos': r.get('pos', ''), 'meaning': r.get('meaning', r.get('target_meaning', '')), 'score': str(score_val), 'color': cl})
        
        total_needed = 50 if selected_pattern == '七十二变' else 60
        while len(all_words) < total_needed:
            all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})

        # 绘制行
        ry = ty + s(25)
        rh = s(22)
        total_rows = (total_needed + 2) // 3
        for row in range(total_rows):
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
                    d.text((cx + cw // 2, ry + rh // 2), str(txt)[:15], fill=fc, font=f, anchor="mm")
                    cx += cw
            ry += rh

        # 保存
        tmp = tempfile.gettempdir()
        fp = os.path.join(tmp, 'shadow_hunter_report.png')
        img.save(fp, dpi=(800, 800))
        with open(fp, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        os.remove(fp)
        return jsonify({'success': True, 'image': b64})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})