# user_data_init.py - 登录时初始化用户独立数据库（仅建库建表，不覆盖已有数据）
from typing import Optional

from user_data_paths import (
    get_user_vocabulary_db_path,
    get_user_exam_stats_db_path,
    get_user_skill_db_path,
)
from user_settings_db import ensure_user_settings
from vocabulary_manager import init_user_vocabulary
from exam_stats_db import ExamStatsDB
from skill_db_schema import ensure_skill_database


def init_all_user_data(
    user_id: str,
    account_name: str = '未设置',
    account_email: Optional[str] = None,
) -> bool:
    """为用户创建/校验所有本地数据库，保留已有内容。"""
    try:
        ensure_user_settings(user_id, account_name=account_name, account_email=account_email)
        init_user_vocabulary(user_id)
        ExamStatsDB(
            get_user_exam_stats_db_path(user_id),
            get_user_vocabulary_db_path(user_id),
        )
        ensure_skill_database(get_user_skill_db_path(user_id))
        return True
    except Exception as e:
        print(f'初始化用户数据失败: {e}')
        return False
