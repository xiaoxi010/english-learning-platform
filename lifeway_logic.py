# lifeway_logic.py - 人生道路解读汇总
from datetime import datetime
from lifeway_calculator import calculate_life_way
from lifeway_interpretation import get_full_interpretation
from lifeway_loader import lifeway_ready
from digital_talent_logic import parse_birth_date, parse_birth_selectors, format_birth_display

NO_DATA = '暂无数据'


def build_lifeway_report(user_name: str, user_name_pinyin: str, year: int, month: int, day: int) -> dict:
    birth_display = f'{year}年{month}月{day}日'
    birth_str = format_birth_display(year, month, day)
    birth_number = birth_str.replace('-', '')
    pinyin = (user_name_pinyin or '').strip().lower()
    if not pinyin.isascii() or not pinyin.isalpha():
        raise ValueError('姓名拼音请使用小写英文字母')

    result = calculate_life_way(pinyin, birth_number)
    interpretation = get_full_interpretation(result)

    return {
        'user_name': (user_name or '').strip() or '未填写',
        'user_name_pinyin': pinyin,
        'birth_display': birth_display,
        'birth_date': birth_str,
        'result': result,
        'interpretation': interpretation,
        'data_ready': lifeway_ready(),
        'calculate_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
