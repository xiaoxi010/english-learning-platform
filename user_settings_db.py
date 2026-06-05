# user_settings_db.py - 每用户独立 SQLite 设置库
import os
import sqlite3
from datetime import datetime
from typing import Dict, Optional

from user_data_paths import get_user_settings_db_path

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CREDITS = 100


def _init_db(conn: sqlite3.Connection):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            account_name TEXT NOT NULL DEFAULT '未设置',
            account_email TEXT NOT NULL DEFAULT '',
            student_id TEXT NOT NULL DEFAULT '',
            credits INTEGER NOT NULL DEFAULT 100,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    conn.commit()


def _default_profile(account_name: str = '未设置', account_email: str = '') -> Dict:
    return {
        'account_name': account_name or '未设置',
        'account_email': account_email or '',
        'student_id': '',
        'credits': DEFAULT_CREDITS,
        # 兼容旧字段名（考试导出等模块）
        'user_name': account_name or '未设置',
    }


def ensure_user_settings(
    user_id: str,
    account_name: str = '未设置',
    account_email: Optional[str] = None,
) -> bool:
    """首次登录时创建用户独立设置数据库"""
    try:
        db_path = get_user_settings_db_path(user_id)
        is_new = not os.path.exists(db_path)
        conn = sqlite3.connect(db_path)
        _init_db(conn)
        row = conn.execute('SELECT id FROM user_profile WHERE id = 1').fetchone()
        now = datetime.now().isoformat(timespec='seconds')
        if not row:
            conn.execute('''
                INSERT INTO user_profile
                (id, account_name, account_email, student_id, credits, created_at, updated_at)
                VALUES (1, ?, ?, '', ?, ?, ?)
            ''', (account_name or '未设置', account_email or '', DEFAULT_CREDITS, now, now))
            conn.commit()
            print(f'已创建用户设置库: {db_path}')
        else:
            if account_email is not None:
                conn.execute(
                    'UPDATE user_profile SET account_email = ?, updated_at = ? WHERE id = 1',
                    (account_email or '', now),
                )
                conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'创建用户设置库失败: {e}')
        return False


def get_user_settings(user_id: str) -> Dict:
    """读取用户设置"""
    try:
        db_path = get_user_settings_db_path(user_id)
        if not os.path.exists(db_path):
            return _default_profile()
        conn = sqlite3.connect(db_path)
        _init_db(conn)
        row = conn.execute('''
            SELECT account_name, account_email, student_id, credits
            FROM user_profile WHERE id = 1
        ''').fetchone()
        conn.close()
        if not row:
            return _default_profile()
        return {
            'account_name': row[0] or '未设置',
            'account_email': row[1] or '',
            'student_id': row[2] or '',
            'credits': row[3] if row[3] is not None else DEFAULT_CREDITS,
            'user_name': row[0] or '未设置',
        }
    except Exception as e:
        print(f'读取用户设置失败: {e}')
        return _default_profile()


def update_user_settings(user_id: str, account_name: str, student_id: str) -> bool:
    """更新账户名称、学号（邮箱由登录同步）"""
    try:
        db_path = get_user_settings_db_path(user_id)
        if not os.path.exists(db_path):
            ensure_user_settings(user_id, account_name=account_name)
        conn = sqlite3.connect(db_path)
        _init_db(conn)
        now = datetime.now().isoformat(timespec='seconds')
        conn.execute('''
            UPDATE user_profile
            SET account_name = ?, student_id = ?, updated_at = ?
            WHERE id = 1
        ''', (account_name, student_id, now))
        if conn.total_changes == 0:
            conn.execute('''
                INSERT INTO user_profile
                (id, account_name, account_email, student_id, credits, created_at, updated_at)
                VALUES (1, ?, '', ?, ?, ?, ?)
            ''', (account_name, student_id, DEFAULT_CREDITS, now, now))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'更新用户设置失败: {e}')
        return False


def update_user_credits(user_id: str, credits: int) -> bool:
    """更新剩余积分"""
    try:
        ensure_user_settings(user_id)
        conn = sqlite3.connect(get_user_settings_db_path(user_id))
        _init_db(conn)
        conn.execute(
            'UPDATE user_profile SET credits = ?, updated_at = ? WHERE id = 1',
            (credits, datetime.now().isoformat(timespec='seconds')),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'更新积分失败: {e}')
        return False


def deduct_credits(user_id: str, amount: int) -> bool:
    """扣除积分，不足则失败"""
    settings = get_user_settings(user_id)
    if settings['credits'] < amount:
        return False
    return update_user_credits(user_id, settings['credits'] - amount)
