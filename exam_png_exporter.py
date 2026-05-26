# exam_png_exporter.py - 完整版（添加阴影迷踪支持 + 考试时间 + 生成时间）
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import os
try:
    from user_config_web import user_config
except ImportError:
    from user_manager import user_config


class ExamPNGExporter:
    """考试记录PNG导出器"""

    def __init__(self):
        pass

    def export(self, record, save_path):
        pattern_name = record.get('pattern_name', '未知版型')
        exam_data = {}
        if record.get('record_details'):
            try:
                exam_data = json.loads(record['record_details'])
            except:
                exam_data = {}

        # 4个版型全部用阴影迷踪格式导出
        if pattern_name == "盗宝大师":
            self._export_treasure_master(record, exam_data, save_path, is_shadow_hunter=True)
        elif pattern_name == "诡影重重":
            self._export_shadow(record, exam_data, save_path, is_shadow_hunter=True)
        elif pattern_name == "三十六计":
            self._export_thirty_six(record, exam_data, save_path, is_shadow_hunter=True)
        elif pattern_name == "七十二变":
            self._export_seventy_two(record, exam_data, save_path, is_shadow_hunter=True)



    # ========== 诡影重重 ==========
    def _export_shadow(self, record, exam_data, save_path, is_shadow_hunter=False):
        try:
            S = 5; W, H = 1290 * S, 1000 * S
            img = Image.new('RGB', (W, H), (26, 26, 42)); d = ImageDraw.Draw(img)
            try:
                ft = ImageFont.truetype("msyh.ttc", 20 * S); fh = ImageFont.truetype("msyh.ttc", 12 * S)
                fi = ImageFont.truetype("msyh.ttc", 10 * S); ftm = ImageFont.truetype("msyh.ttc", 9 * S)
                fth = ImageFont.truetype("msyh.ttc", 10 * S); ftc = ImageFont.truetype("msyh.ttc", 9 * S)
                fe = ImageFont.truetype("arial.ttf", 9 * S)
            except: ft=fh=fi=ftm=fth=ftc=fe=ImageFont.load_default()
            def s(v): return int(v * S)

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_user, current_student_id = user_config.get_current_user()
            group_name = record.get('group_name', '')
            basic_score = record.get('basic_score', 0) or 0
            shadow_score = record.get('shadow_score', 0) or 0
            total_score = record.get('total_score', record.get('score', 0))
            is_passed = record.get('is_passed', False)
            exam_time = record.get('exam_time', '')
            pattern_data = exam_data.get('pattern_data', {})
            shadow_words = pattern_data.get('shadow_words', [])
            basic_words = exam_data.get('basic_words', [])
            actual_pattern = exam_data.get('pattern_name', '诡影重重')
            yesterday_group = record.get('yesterday_group', '') if not is_shadow_hunter else ''

            title = "阴影迷踪考试总成绩报告" if is_shadow_hunter else "诡影重重考试总成绩报告"
            d.text((W // 2, s(20)), title, fill=(255, 107, 53) if is_shadow_hunter else (255, 215, 0), font=ft, anchor="ma")

            top_y = s(55); left_x = s(40); left_w = (W - s(80)) // 2 - s(10)
            top_h = s(130) if is_shadow_hunter else s(110)
            d.rectangle([left_x, top_y, left_x + left_w, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
            ix, iy = left_x + s(10), top_y + s(8)
            d.text((ix, iy), "姓名：", fill=(52, 152, 219), font=fh); d.text((ix + s(42), iy), current_user, fill=(255, 255, 255), font=fi)
            d.text((ix + s(130), iy), "学号：", fill=(52, 152, 219), font=fh); d.text((ix + s(175), iy), current_student_id, fill=(255, 255, 255), font=fi)
            iy += s(18)
            d.text((ix, iy), "今日组别：", fill=(52, 152, 219), font=fh); d.text((ix + s(60), iy), group_name, fill=(255, 255, 255), font=fi)
            if is_shadow_hunter:
                d.text((ix + s(130), iy), "版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(165), iy), "阴影迷踪", fill=(255, 107, 53), font=fi)
                iy += s(18)
                d.text((ix, iy), "抽取版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(60), iy), actual_pattern, fill=(255, 107, 53), font=fi)
            else:
                d.text((ix + s(130), iy), "昨日组别：", fill=(52, 152, 219), font=fh); d.text((ix + s(175), iy), yesterday_group, fill=(255, 255, 255), font=fi)
                iy += s(18)
                d.text((ix, iy), "版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(42), iy), "诡影重重", fill=(255, 255, 255), font=fi)
            iy += s(18)
            bc = (46, 204, 113) if basic_score >= 18 else (231, 76, 96); sc = (46, 204, 113) if shadow_score >= 15 else (231, 76, 96)
            tc = (46, 204, 113) if is_passed else (231, 76, 96)
            d.text((ix, iy), f"基础词汇：{basic_score:.2f}/30", fill=bc, font=fh)
            d.text((ix + s(120), iy), f"诡影重重：{shadow_score:.2f}/20", fill=sc, font=fh)
            iy += s(18)
            d.text((ix, iy), f"总得分：{total_score:.2f}/50", fill=tc, font=fh)
            iy += s(18)
            d.text((ix, iy), f"考试时间：{exam_time}", fill=(149, 165, 166), font=ftm)
            d.text((ix + s(300), iy), f"生成时间：{current_time}", fill=(149, 165, 166), font=ftm)

            rx = left_x + left_w + s(20); rw = left_w
            d.rectangle([rx, top_y, rx + rw, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
            pass_photo_path, fail_photo_path = user_config.get_photo_paths()
            pp = pass_photo_path if is_passed else fail_photo_path
            if os.path.exists(pp):
                pi = Image.open(pp).resize((s(140), s(85)), Image.Resampling.LANCZOS)
                img.paste(pi, (rx + (rw - s(140)) // 2, top_y + (top_h - s(85)) // 2))
            else:
                d.text((rx + rw // 2, top_y + top_h // 2), "通过" if is_passed else "挂科", fill=tc, font=fh, anchor="mm")

            ty = top_y + top_h + s(15); cols4 = [s(140), s(50), s(130), s(50)]; headers4 = ["单词", "词性", "汉译", "得分"]; gap = s(12)
            hx = s(45)
            for grp in range(3):
                for ci, (hdr, cw) in enumerate(zip(headers4, cols4)):
                    bg = (255, 215, 0) if ci == 0 else ((52, 152, 219) if ci == 1 else (42, 42, 58))
                    d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                    d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm"); hx += cw
                hx += gap

            all_words = []
            for bw in basic_words:
                sv = bw.get('score', 0); sc_display = f"{sv:.2f}" if sv >= 0.99 else (f"{sv:.2f}" if sv >= 0.74 else "0.00")
                cl = (46, 204, 113) if sv >= 0.99 else ((255, 215, 0) if sv >= 0.74 else (231, 76, 96))
                all_words.append({'word': bw.get('word','-'), 'pos': bw.get('part_of_speech','-'), 'meaning': bw.get('meaning','-'), 'score': sc_display, 'color': cl})
            while len(all_words) < 30: all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
            for sw in shadow_words:
                sv = sw.get('score', 0); sc_display = f"{sv:.2f}"
                cl = (46, 204, 113) if sv >= 1 else ((255, 215, 0) if sv >= 0.75 else (231, 76, 96))
                all_words.append({'word': sw.get('word','-'), 'pos': sw.get('part_of_speech','-'), 'meaning': sw.get('meaning','-'), 'score': sc_display, 'color': cl})
            while len(all_words) < 60: all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})

            ry = ty + s(25); rh = s(22)
            for row in range(20):
                bg_row = (42, 42, 58) if row % 2 == 0 else (37, 37, 53)
                d.rectangle([s(40), ry, s(40) + s(35), ry + rh], fill=(26, 26, 42), outline=(255, 255, 255), width=1)
                d.text((s(40) + s(17), ry + rh // 2), f"{(row+1):02d}", fill=(52, 152, 219), font=ftc, anchor="mm")
                cx_start = s(40) + s(35)
                for col in range(3):
                    idx = row * 3 + col; cx = cx_start + col * (sum(cols4) + gap)
                    if idx < len(all_words): w = all_words[idx]; vals = [w['word'], w['pos'], w['meaning'], w['score']]
                    else: vals = ['-', '-', '-', '-']; w = {'color': (127, 140, 141)}
                    for ci, (cw, txt) in enumerate(zip(cols4, vals)):
                        d.rectangle([cx, ry, cx + cw, ry + rh], fill=bg_row, outline=(255, 255, 255), width=1)
                        fc = w['color'] if ci == 0 or ci == 3 else ((52, 152, 219) if ci == 1 else (255, 255, 255))
                        f = fe if (ci == 0 or ci == 3) else ftc
                        d.text((cx + cw // 2, ry + rh // 2), str(txt)[:15], fill=fc, font=f, anchor="mm"); cx += cw
                ry += rh
            img.save(save_path, dpi=(800, 800))
        except Exception as e:
            print(f"导出诡影重重失败: {e}"); import traceback; traceback.print_exc()

    # ========== 盗宝大师 ==========
    def _export_treasure_master(self, record, exam_data, save_path, is_shadow_hunter=False):
        try:
            S = 5; W, H = 1290 * S, 950 * S
            img = Image.new('RGB', (W, H), (26, 26, 42)); d = ImageDraw.Draw(img)
            try:
                ft = ImageFont.truetype("msyh.ttc", 20 * S); fh = ImageFont.truetype("msyh.ttc", 12 * S)
                fi = ImageFont.truetype("msyh.ttc", 10 * S); ftm = ImageFont.truetype("msyh.ttc", 9 * S)
                fth = ImageFont.truetype("msyh.ttc", 10 * S); ftc = ImageFont.truetype("msyh.ttc", 9 * S)
                fe = ImageFont.truetype("arial.ttf", 9 * S)
            except: ft=fh=fi=ftm=fth=ftc=fe=ImageFont.load_default()
            def s(v): return int(v * S)

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_user, current_student_id = user_config.get_current_user()
            group_name = record.get('group_name', '')
            basic_score = record.get('basic_score', 0) or 0
            treasure_score = record.get('shadow_score', 0) or 0
            total_score = record.get('total_score', record.get('score', 0))
            is_passed = record.get('is_passed', False)
            exam_time = record.get('exam_time', '')
            pattern_data = exam_data.get('pattern_data', {})
            treasure_words = pattern_data.get('treasure_words', [])
            true_treasure = pattern_data.get('true_treasure', 1)
            found_true_treasure = pattern_data.get('found_true_treasure', False)
            basic_words = exam_data.get('basic_words', [])
            actual_pattern = exam_data.get('pattern_name', '盗宝大师')
            TREASURE_NAMES = ['青山', '寒山', '沧山', '暮山', '尘山']

            title = "阴影迷踪考试总成绩报告" if is_shadow_hunter else "盗宝大师考试总成绩报告"
            d.text((W // 2, s(20)), title, fill=(255, 107, 53) if is_shadow_hunter else (255, 215, 0), font=ft, anchor="ma")

            top_y = s(55); left_x = s(40); left_w = (W - s(80)) // 2 - s(10)
            top_h = s(150) if is_shadow_hunter else s(130)
            d.rectangle([left_x, top_y, left_x + left_w, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
            ix, iy = left_x + s(10), top_y + s(8)
            d.text((ix, iy), "姓名：", fill=(52, 152, 219), font=fh); d.text((ix + s(42), iy), current_user, fill=(255, 255, 255), font=fi)
            d.text((ix + s(130), iy), "学号：", fill=(52, 152, 219), font=fh); d.text((ix + s(175), iy), current_student_id, fill=(255, 255, 255), font=fi)
            iy += s(18)
            d.text((ix, iy), "今日组别：", fill=(52, 152, 219), font=fh); d.text((ix + s(60), iy), group_name, fill=(255, 255, 255), font=fi)
            if is_shadow_hunter:
                d.text((ix + s(130), iy), "版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(165), iy), "阴影迷踪", fill=(255, 107, 53), font=fi)
                iy += s(18)
                d.text((ix, iy), "抽取版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(60), iy), actual_pattern, fill=(255, 107, 53), font=fi)
            else:
                d.text((ix + s(130), iy), "版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(165), iy), "盗宝大师", fill=(255, 255, 255), font=fi)
            iy += s(18)
            bc = (46, 204, 113) if basic_score >= 18 else (231, 76, 96); sc = (46, 204, 113) if treasure_score >= 16 else (231, 76, 96)
            tc = (46, 204, 113) if is_passed else (231, 76, 96)
            d.text((ix, iy), f"基础词汇：{basic_score:.2f}/30", fill=bc, font=fh)
            d.text((ix + s(120), iy), f"盗宝大师：{treasure_score}/20", fill=sc, font=fh)
            iy += s(18)
            d.text((ix, iy), f"总得分：{total_score:.2f}/50", fill=tc, font=fh)
            iy += s(18)
            d.text((ix, iy), "真宝藏：", fill=(52, 152, 219), font=fh)
            true_name = TREASURE_NAMES[true_treasure - 1] if 1 <= true_treasure <= 5 else f"宝藏{true_treasure}"
            d.text((ix + s(55), iy), true_name, fill=(255, 215, 0), font=fh)
            d.text((ix + s(110), iy), f"找到：{'是' if found_true_treasure else '否'}", fill=tc, font=fh)
            iy += s(18)
            d.text((ix, iy), f"考试时间：{exam_time}", fill=(149, 165, 166), font=ftm)
            d.text((ix + s(300), iy), f"生成时间：{current_time}", fill=(149, 165, 166), font=ftm)

            rx = left_x + left_w + s(20); rw = left_w
            d.rectangle([rx, top_y, rx + rw, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
            pass_photo_path, fail_photo_path = user_config.get_photo_paths()
            pp = pass_photo_path if is_passed else fail_photo_path
            if os.path.exists(pp):
                pi = Image.open(pp).resize((s(140), s(85)), Image.Resampling.LANCZOS)
                img.paste(pi, (rx + (rw - s(140)) // 2, top_y + (top_h - s(85)) // 2))
            else:
                d.text((rx + rw // 2, top_y + top_h // 2), "通过" if is_passed else "挂科", fill=tc, font=fh, anchor="mm")

            ty = top_y + top_h + s(15); cols4 = [s(140), s(50), s(130), s(50)]; headers4 = ["单词", "词性", "汉译", "得分"]; gap = s(12)
            hx = s(45)
            for grp in range(3):
                for ci, (hdr, cw) in enumerate(zip(headers4, cols4)):
                    bg = (255, 215, 0) if ci == 0 else ((52, 152, 219) if ci == 1 else (42, 42, 58))
                    d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                    d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm"); hx += cw
                hx += gap

            all_words = []
            for bw in basic_words:
                sv = bw.get('score', 0); sc_display = "1.00" if sv >= 0.99 else "0.00"
                cl = (46, 204, 113) if sv >= 0.99 else (231, 76, 96)
                all_words.append({'word': bw.get('word','-'), 'pos': bw.get('part_of_speech','-'), 'meaning': bw.get('meaning','-'), 'score': sc_display, 'color': cl})
            while len(all_words) < 30: all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
            for tw in treasure_words:
                is_c = tw.get('is_correct', False); sc_display = "1.00" if is_c else "0.00"
                cl = (46, 204, 113) if is_c else (231, 76, 96)
                all_words.append({'word': tw.get('word','-'), 'pos': tw.get('part_of_speech','-'), 'meaning': tw.get('meaning','-'), 'score': sc_display, 'color': cl})
            while len(all_words) < 50: all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})

            ry = ty + s(25); rh = s(22); total_rows = 17
            for row in range(total_rows):
                bg_row = (42, 42, 58) if row % 2 == 0 else (37, 37, 53)
                d.rectangle([s(40), ry, s(40) + s(35), ry + rh], fill=(26, 26, 42), outline=(255, 255, 255), width=1)
                d.text((s(40) + s(17), ry + rh // 2), f"{(row+1):02d}", fill=(52, 152, 219), font=ftc, anchor="mm")
                cx_start = s(40) + s(35)
                for col in range(3):
                    idx = row * 3 + col; cx = cx_start + col * (sum(cols4) + gap)
                    if idx < len(all_words): w = all_words[idx]; vals = [w['word'], w['pos'], w['meaning'], w['score']]
                    else: vals = ['-', '-', '-', '-']; w = {'color': (127, 140, 141)}
                    for ci, (cw, txt) in enumerate(zip(cols4, vals)):
                        d.rectangle([cx, ry, cx + cw, ry + rh], fill=bg_row, outline=(255, 255, 255), width=1)
                        fc = w['color'] if ci == 0 or ci == 3 else ((52, 152, 219) if ci == 1 else (255, 255, 255))
                        f = fe if (ci == 0 or ci == 3) else ftc
                        d.text((cx + cw // 2, ry + rh // 2), str(txt)[:15], fill=fc, font=f, anchor="mm"); cx += cw
                ry += rh
            img.save(save_path, dpi=(800, 800))
        except Exception as e:
            print(f"导出盗宝大师失败: {e}"); import traceback; traceback.print_exc()

    # ========== 七十二变 ==========
    def _export_seventy_two(self, record, exam_data, save_path, is_shadow_hunter=False):
        try:
            S = 5; W, H = 1290 * S, 950 * S
            img = Image.new('RGB', (W, H), (26, 26, 42)); d = ImageDraw.Draw(img)
            try:
                ft = ImageFont.truetype("msyh.ttc", 20 * S); fh = ImageFont.truetype("msyh.ttc", 12 * S)
                fi = ImageFont.truetype("msyh.ttc", 10 * S); ftm = ImageFont.truetype("msyh.ttc", 9 * S)
                fth = ImageFont.truetype("msyh.ttc", 10 * S); ftc = ImageFont.truetype("msyh.ttc", 9 * S)
                fe = ImageFont.truetype("arial.ttf", 9 * S); fs = ImageFont.truetype("arial.ttf", 10 * S)
            except: ft=fh=fi=ftm=fth=ftc=fe=fs=ImageFont.load_default()
            def s(v): return int(v * S)

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_user, current_student_id = user_config.get_current_user()
            group_name = record.get('group_name', '')
            basic_score = record.get('basic_score', 0) or 0
            strategy_score = record.get('shadow_score', 0) or 0
            total_score = record.get('total_score', record.get('score', 0))
            is_passed = record.get('is_passed', False)
            exam_time = record.get('exam_time', '')
            pattern_data = exam_data.get('pattern_data', {})
            word_cards = pattern_data.get('word_cards', [])
            basic_words = exam_data.get('basic_words', [])
            actual_pattern = exam_data.get('pattern_name', '七十二变')

            title = "阴影迷踪考试总成绩报告" if is_shadow_hunter else "七十二变考试总成绩报告"
            d.text((W // 2, s(20)), title, fill=(255, 107, 53), font=ft, anchor="ma")

            top_y = s(55); left_x = s(40); left_w = (W - s(80)) // 2 - s(10)
            top_h = s(130) if is_shadow_hunter else s(110)
            d.rectangle([left_x, top_y, left_x + left_w, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
            ix, iy = left_x + s(10), top_y + s(8)
            d.text((ix, iy), "姓名：", fill=(52, 152, 219), font=fh); d.text((ix + s(42), iy), current_user, fill=(255, 255, 255), font=fi)
            d.text((ix + s(130), iy), "学号：", fill=(52, 152, 219), font=fh); d.text((ix + s(175), iy), current_student_id, fill=(255, 255, 255), font=fi)
            iy += s(18)
            d.text((ix, iy), "今日组别：", fill=(52, 152, 219), font=fh); d.text((ix + s(60), iy), group_name, fill=(255, 255, 255), font=fi)
            if is_shadow_hunter:
                d.text((ix + s(130), iy), "版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(165), iy), "阴影迷踪", fill=(255, 107, 53), font=fi)
                iy += s(18)
                d.text((ix, iy), "抽取版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(60), iy), actual_pattern, fill=(255, 107, 53), font=fi)
            else:
                d.text((ix + s(130), iy), "昨日组别：", fill=(52, 152, 219), font=fh); d.text((ix + s(175), iy), record.get('yesterday_group',''), fill=(255, 255, 255), font=fi)
                iy += s(18)
                d.text((ix, iy), "版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(42), iy), "七十二变", fill=(255, 255, 255), font=fi)
            iy += s(18)
            bc = (46, 204, 113) if basic_score >= 18 else (231, 76, 96); sc = (46, 204, 113) if strategy_score >= 13 else (231, 76, 96)
            tc = (46, 204, 113) if is_passed else (231, 76, 96)
            d.text((ix, iy), f"基础词汇：{basic_score:.2f}/30", fill=bc, font=fh)
            d.text((ix + s(120), iy), f"版型分数：{strategy_score}/20", fill=sc, font=fh)
            iy += s(18)
            d.text((ix, iy), f"总得分：{total_score:.2f}/50", fill=tc, font=fh)
            iy += s(18)
            d.text((ix, iy), f"考试时间：{exam_time}", fill=(149, 165, 166), font=ftm)
            d.text((ix + s(300), iy), f"生成时间：{current_time}", fill=(149, 165, 166), font=ftm)

            rx = left_x + left_w + s(20); rw = left_w
            d.rectangle([rx, top_y, rx + rw, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
            pass_photo_path, fail_photo_path = user_config.get_photo_paths()
            pp = pass_photo_path if is_passed else fail_photo_path
            if os.path.exists(pp):
                pi = Image.open(pp).resize((s(140), s(85)), Image.Resampling.LANCZOS)
                img.paste(pi, (rx + (rw - s(140)) // 2, top_y + (top_h - s(85)) // 2))
            else:
                d.text((rx + rw // 2, top_y + top_h // 2), "通过" if is_passed else "挂科", fill=tc, font=fh, anchor="mm")

            ty = top_y + top_h + s(15); cols4 = [s(140), s(50), s(130), s(50)]; headers4 = ["单词", "词性", "汉译", "得分"]; gap = s(12)
            hx = s(45)
            for grp in range(3):
                for ci, (hdr, cw) in enumerate(zip(headers4, cols4)):
                    bg = (255, 107, 53) if ci == 0 else ((52, 152, 219) if ci == 1 else (42, 42, 58))
                    d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                    d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm"); hx += cw
                hx += gap

            all_words = []
            for bw in basic_words:
                sv = bw.get('score', 0); sc_display = "1.00" if sv >= 0.99 else "0.00"
                cl = (46, 204, 113) if sv >= 0.99 else (231, 76, 96)
                all_words.append({'word': bw.get('word','-'), 'pos': bw.get('part_of_speech','-'), 'meaning': bw.get('meaning','-'), 'score': sc_display, 'color': cl})
            while len(all_words) < 30: all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
            for wc in word_cards:
                is_c = wc.get('is_correct', False); sc_display = "1.00" if is_c else "0.00"
                cl = (46, 204, 113) if is_c else (231, 76, 96)
                all_words.append({'word': wc.get('word','-'), 'pos': wc.get('part_of_speech','-'), 'meaning': wc.get('meaning','-'), 'score': sc_display, 'color': cl})
            while len(all_words) < 50: all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})

            ry = ty + s(25); rh = s(22); total_rows = 17
            for row in range(total_rows):
                bg_row = (42, 42, 58) if row % 2 == 0 else (37, 37, 53)
                d.rectangle([s(40), ry, s(40) + s(35), ry + rh], fill=(26, 26, 42), outline=(255, 255, 255), width=1)
                d.text((s(40) + s(17), ry + rh // 2), f"{(row+1):02d}", fill=(52, 152, 219), font=ftc, anchor="mm")
                cx_start = s(40) + s(35)
                for col in range(3):
                    idx = row * 3 + col; cx = cx_start + col * (sum(cols4) + gap)
                    if idx < len(all_words): w = all_words[idx]; vals = [w['word'], w['pos'], w['meaning'], w['score']]
                    else: vals = ['-', '-', '-', '-']; w = {'color': (127, 140, 141)}
                    for ci, (cw, txt) in enumerate(zip(cols4, vals)):
                        d.rectangle([cx, ry, cx + cw, ry + rh], fill=bg_row, outline=(255, 255, 255), width=1)
                        fc = w['color'] if ci == 0 or ci == 3 else ((52, 152, 219) if ci == 1 else (255, 255, 255))
                        f = fe if (ci == 0 or ci == 3) else ftc
                        d.text((cx + cw // 2, ry + rh // 2), str(txt)[:15], fill=fc, font=f, anchor="mm"); cx += cw
                ry += rh
            img.save(save_path, dpi=(800, 800))
        except Exception as e:
            print(f"导出七十二变失败: {e}"); import traceback; traceback.print_exc()

    # ========== 三十六计 ==========
    def _export_thirty_six(self, record, exam_data, save_path, is_shadow_hunter=False):
        try:
            S = 5; W, H = 1290 * S, 950 * S
            img = Image.new('RGB', (W, H), (26, 26, 42)); d = ImageDraw.Draw(img)
            try:
                ft = ImageFont.truetype("msyh.ttc", 20 * S); fh = ImageFont.truetype("msyh.ttc", 12 * S)
                fi = ImageFont.truetype("msyh.ttc", 10 * S); ftm = ImageFont.truetype("msyh.ttc", 9 * S)
                fth = ImageFont.truetype("msyh.ttc", 10 * S); ftc = ImageFont.truetype("msyh.ttc", 9 * S)
                fe = ImageFont.truetype("arial.ttf", 9 * S); fs = ImageFont.truetype("arial.ttf", 10 * S)
            except: ft=fh=fi=ftm=fth=ftc=fe=fs=ImageFont.load_default()
            def s(v): return int(v * S)

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_user, current_student_id = user_config.get_current_user()
            group_name = record.get('group_name', '')
            basic_score = record.get('basic_score', 0) or 0
            strategy_score = record.get('shadow_score', 0) or 0
            total_score = record.get('total_score', record.get('score', 0))
            is_passed = record.get('is_passed', False)
            exam_time = record.get('exam_time', '')
            pattern_data = exam_data.get('pattern_data', {})
            all_words_36 = pattern_data.get('all_words', [])
            basic_words = exam_data.get('basic_words', [])
            actual_pattern = exam_data.get('pattern_name', '三十六计')

            title = "阴影迷踪考试总成绩报告" if is_shadow_hunter else "三十六计考试总成绩报告"
            d.text((W // 2, s(20)), title, fill=(255, 107, 53), font=ft, anchor="ma")

            top_y = s(55); left_x = s(40); left_w = (W - s(80)) // 2 - s(10)
            top_h = s(130) if is_shadow_hunter else s(110)
            d.rectangle([left_x, top_y, left_x + left_w, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
            ix, iy = left_x + s(10), top_y + s(8)
            d.text((ix, iy), "姓名：", fill=(52, 152, 219), font=fh); d.text((ix + s(42), iy), current_user, fill=(255, 255, 255), font=fi)
            d.text((ix + s(130), iy), "学号：", fill=(52, 152, 219), font=fh); d.text((ix + s(175), iy), current_student_id, fill=(255, 255, 255), font=fi)
            iy += s(18)
            d.text((ix, iy), "今日组别：", fill=(52, 152, 219), font=fh); d.text((ix + s(60), iy), group_name, fill=(255, 255, 255), font=fi)
            if is_shadow_hunter:
                d.text((ix + s(130), iy), "版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(165), iy), "阴影迷踪", fill=(255, 107, 53), font=fi)
                iy += s(18)
                d.text((ix, iy), "抽取版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(60), iy), actual_pattern, fill=(255, 107, 53), font=fi)
            else:
                d.text((ix + s(130), iy), "版型：", fill=(52, 152, 219), font=fh); d.text((ix + s(165), iy), "三十六计", fill=(255, 255, 255), font=fi)
            iy += s(18)
            bc = (46, 204, 113) if basic_score >= 18 else (231, 76, 96); sc = (46, 204, 113) if strategy_score >= 17 else (231, 76, 96)
            tc = (46, 204, 113) if is_passed else (231, 76, 96)
            d.text((ix, iy), f"基础词汇：{basic_score:.2f}/30", fill=bc, font=fh)
            d.text((ix + s(120), iy), f"版型分数：{strategy_score}/20", fill=sc, font=fh)
            iy += s(18)
            d.text((ix, iy), f"总得分：{total_score:.2f}/50", fill=tc, font=fh)
            iy += s(18)
            d.text((ix, iy), f"考试时间：{exam_time}", fill=(149, 165, 166), font=ftm)
            d.text((ix + s(300), iy), f"生成时间：{current_time}", fill=(149, 165, 166), font=ftm)

            rx = left_x + left_w + s(20); rw = left_w
            d.rectangle([rx, top_y, rx + rw, top_y + top_h], fill=(42, 42, 58), outline=(255, 255, 255), width=1)
            pass_photo_path, fail_photo_path = user_config.get_photo_paths()
            pp = pass_photo_path if is_passed else fail_photo_path
            if os.path.exists(pp):
                pi = Image.open(pp).resize((s(140), s(85)), Image.Resampling.LANCZOS)
                img.paste(pi, (rx + (rw - s(140)) // 2, top_y + (top_h - s(85)) // 2))
            else:
                d.text((rx + rw // 2, top_y + top_h // 2), "通过" if is_passed else "挂科", fill=tc, font=fh, anchor="mm")

            ty = top_y + top_h + s(15); cols4 = [s(140), s(50), s(130), s(50)]; headers4 = ["单词", "词性", "汉译", "得分"]; gap = s(12)
            hx = s(45)
            for grp in range(3):
                for ci, (hdr, cw) in enumerate(zip(headers4, cols4)):
                    bg = (255, 107, 53) if ci == 0 else ((52, 152, 219) if ci == 1 else (42, 42, 58))
                    d.rectangle([hx, ty, hx + cw, ty + s(22)], fill=bg, outline=(255, 255, 255), width=1)
                    d.text((hx + cw // 2, ty + s(11)), hdr, fill=(255, 255, 255), font=fth, anchor="mm"); hx += cw
                hx += gap

            all_words = []
            for bw in basic_words:
                sv = bw.get('score', 0); sc_display = "1.00" if sv >= 0.99 else "0.00"
                cl = (46, 204, 113) if sv >= 0.99 else (231, 76, 96)
                all_words.append({'word': bw.get('word','-'), 'pos': bw.get('part_of_speech','-'), 'meaning': bw.get('meaning','-'), 'score': sc_display, 'color': cl})
            while len(all_words) < 30: all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})
            for aw in all_words_36:
                is_c = aw.get('is_correct', False); sc_display = "1.00" if is_c else "0.00"
                cl = (46, 204, 113) if is_c else (231, 76, 96)
                all_words.append({'word': aw.get('word','-'), 'pos': aw.get('part_of_speech','-'), 'meaning': aw.get('target_meaning', aw.get('meaning','-')), 'score': sc_display, 'color': cl})
            while len(all_words) < 60: all_words.append({'word': '-', 'pos': '-', 'meaning': '-', 'score': '0.00', 'color': (127, 140, 141)})

            ry = ty + s(25); rh = s(22); total_rows = 20
            for row in range(total_rows):
                bg_row = (42, 42, 58) if row % 2 == 0 else (37, 37, 53)
                d.rectangle([s(40), ry, s(40) + s(35), ry + rh], fill=(26, 26, 42), outline=(255, 255, 255), width=1)
                d.text((s(40) + s(17), ry + rh // 2), f"{(row+1):02d}", fill=(52, 152, 219), font=ftc, anchor="mm")
                cx_start = s(40) + s(35)
                for col in range(3):
                    idx = row * 3 + col; cx = cx_start + col * (sum(cols4) + gap)
                    if idx < len(all_words): w = all_words[idx]; vals = [w['word'], w['pos'], w['meaning'], w['score']]
                    else: vals = ['-', '-', '-', '-']; w = {'color': (127, 140, 141)}
                    for ci, (cw, txt) in enumerate(zip(cols4, vals)):
                        d.rectangle([cx, ry, cx + cw, ry + rh], fill=bg_row, outline=(255, 255, 255), width=1)
                        fc = w['color'] if ci == 0 or ci == 3 else ((52, 152, 219) if ci == 1 else (255, 255, 255))
                        f = fe if (ci == 0 or ci == 3) else ftc
                        d.text((cx + cw // 2, ry + rh // 2), str(txt)[:15], fill=fc, font=f, anchor="mm"); cx += cw
                ry += rh
            img.save(save_path, dpi=(800, 800))
        except Exception as e:
            print(f"导出三十六计失败: {e}"); import traceback; traceback.print_exc()

    # ========== 意言译语 ==========
    def _export_meaning_language(self, record, exam_data, save_path, is_shadow_hunter=False):
        # 保持原样，略
        pass

    # ========== 万圣之夜 ==========
    def _export_halloween(self, record, exam_data, save_path, is_shadow_hunter=False):
        # 保持原样，略
        pass


def export_exam_record(record, save_path):
    exporter = ExamPNGExporter()
    exporter.export(record, save_path)