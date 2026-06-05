# eysenck_logic.py
from datetime import datetime

from eysenck_calc import run_eysenck_test
from eysenck_loader import load_meta, load_questions
from eysenck_report_vm import prepare_report_view_model

OPTIONS = ('是', '否', '不确定')


def parse_answers(form, total):
    answers = []
    for i in range(total):
        v = (form.get(f'ans_{i}') or '').strip()
        if v not in OPTIONS:
            answers.append('')
        else:
            answers.append(v)
    return answers


def build_eysenck_report(user_name, answers, started_at_ms=None, finished_at_ms=None):
    questions = load_questions()
    n = len(questions)
    if n != 210:
        raise ValueError('艾克森题库未加载完整（需 210 题）')

    if len(answers) < n:
        answers = list(answers) + [''] * (n - len(answers))
    answers = answers[:n]

    for i, a in enumerate(answers):
        if a not in OPTIONS:
            raise ValueError(f'请完成第 {i + 1} 题')

    now = finished_at_ms or int(datetime.now().timestamp() * 1000)
    started = started_at_ms or now
    duration_minutes = max(1, round((now - started) / 60000))
    is_valid = 10 <= duration_minutes <= 40

    finished_dt = datetime.fromtimestamp(now / 1000)
    user_info = {
        'userName': user_name,
        'answerTime': finished_dt.strftime('%Y-%m-%d %H:%M'),
        'answerDuration': duration_minutes,
        'isValid': is_valid,
    }

    result = run_eysenck_test(answers)
    if not result:
        raise ValueError('计分失败，请检查答案是否完整')

    vm = prepare_report_view_model(result, user_info)
    meta = load_meta()

    chart_rows = []
    for d in vm.get('dimensions') or []:
        chart_rows.append({
            'id': d.get('id'),
            'name': d.get('dimensionBipolarTitle') or d.get('reportDimShortName') or d.get('name'),
            'raw_score': d.get('rawScore'),
            'chart_max': d.get('chartMax', 30),
            'score_text': d.get('scoreSlashMax') or '—',
            'is_unstable': d.get('isUnstable'),
            'state_label': d.get('stateTraitLabel'),
            'score_band_high': d.get('scoreBandIsHigh'),
        })

    return {
        'user_name': user_name,
        'vm': vm,
        'meta': meta,
        'chart_rows': chart_rows,
        'validity_text': '有效' if is_valid else '待确认',
        'duration_minutes': duration_minutes,
        'report_id': f"EYS-{vm.get('currentDate', '')}-{vm.get('seqId', '')}",
        'calculate_time': user_info['answerTime'],
        'data_ready': True,
    }
