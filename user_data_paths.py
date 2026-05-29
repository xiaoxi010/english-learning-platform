# user_data_paths.py - 每用户本地数据目录与数据库路径
import os
import re
import hashlib

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(_BASE_DIR, 'user_data')


def safe_user_key(user_id: str) -> str:
    safe = re.sub(r'[^\w\-]', '_', user_id or '')
    safe = safe.strip('_')[:64]
    if not safe:
        safe = hashlib.sha256((user_id or 'unknown').encode()).hexdigest()[:32]
    return safe


def get_user_data_dir(user_id: str) -> str:
    user_dir = os.path.join(USER_DATA_DIR, safe_user_key(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def get_user_vocabulary_db_path(user_id: str) -> str:
    return os.path.join(get_user_data_dir(user_id), 'vocabulary.db')


def get_user_settings_db_path(user_id: str) -> str:
    return os.path.join(get_user_data_dir(user_id), 'settings.db')


def get_user_exam_stats_db_path(user_id: str) -> str:
    return os.path.join(get_user_data_dir(user_id), 'exam_stats.db')


def get_user_skill_db_path(user_id: str) -> str:
    return os.path.join(get_user_data_dir(user_id), 'skill_database.db')


def get_user_skill_upload_dir(user_id: str) -> str:
    path = os.path.join(get_user_data_dir(user_id), 'skill_uploads')
    os.makedirs(path, exist_ok=True)
    return path


def get_user_skill_export_dir(user_id: str) -> str:
    path = os.path.join(get_user_data_dir(user_id), 'skill_exports')
    os.makedirs(path, exist_ok=True)
    return path
