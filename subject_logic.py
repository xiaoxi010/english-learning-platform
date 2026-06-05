# subject_logic.py - 学科能力测评入口
from subject_loader import load_ability_json, load_comprehensive_json, find_ability_by_code, find_comprehensive_by_code, ability_ready
from subject_report_logic import build_full_subject_report
from digital_talent_logic import parse_birth_date, parse_birth_selectors, format_birth_display
import re


def build_subject_report(name, gender, year, month, day, **profile):
    birth = format_birth_display(year, month, day)
    birth_number = re.sub(r'\D', '', birth)
    if int(year) < 2000:
        raise ValueError('本测评仅支持2000年1月1日及以后出生的青少年')

    raw_ab = load_ability_json()
    if not raw_ab:
        raise ValueError('学科能力数据库未加载，请放置 data/subjectAbilityData.json')

    code = __import__('subject_code', fromlist=['get_subject_code_from_birth']).get_subject_code_from_birth(birth_number)
    row = find_ability_by_code(raw_ab, code)
    if not row:
        raise ValueError(f'暂无学科码「{code}」对应的学科能力数据')

    raw_co = load_comprehensive_json()
    comp_row = find_comprehensive_by_code(raw_co, code) if raw_co else None

    report = build_full_subject_report(name, gender, birth_number, row, comp_row)
    report['data_ready'] = ability_ready()
    report['comp_data_ready'] = comp_row is not None
    report.update({k: v for k, v in profile.items() if v})
    return report
