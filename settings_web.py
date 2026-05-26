# settings_web.py - 用户设置管理
from flask import Blueprint, render_template, request, jsonify
import sqlite3, os

settings_bp = Blueprint('settings', __name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.db")


def init_db():
    """初始化设置数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    # 插入默认值
    defaults = {'user_name': '崔朕', 'student_id': '20231719'}
    for k, v in defaults.items():
        c.execute('INSERT OR IGNORE INTO user_settings (key, value) VALUES (?, ?)', (k, v))
    conn.commit()
    conn.close()


def get_setting(key):
    """获取单个设置"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM user_settings WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''


def get_all_settings():
    """获取所有设置"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT key, value FROM user_settings')
    rows = c.fetchall()
    conn.close()
    return {k: v for k, v in rows}


def set_setting(key, value):
    """更新设置"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()


# 初始化数据库
init_db()


@settings_bp.route('/settings')
def settings_page():
    """设置页面"""
    settings = get_all_settings()
    return render_template('settings.html',
                         user_name=settings.get('user_name', ''),
                         student_id=settings.get('student_id', ''))


@settings_bp.route('/api/settings/save', methods=['POST'])
def save_settings():
    """保存设置"""
    data = request.get_json()
    user_name = data.get('user_name', '').strip()
    student_id = data.get('student_id', '').strip()
    
    if not user_name:
        return jsonify({'success': False, 'message': '姓名不能为空'})
    
    set_setting('user_name', user_name)
    set_setting('student_id', student_id)
    
    return jsonify({'success': True, 'message': '设置已保存'})


@settings_bp.route('/api/settings/get', methods=['GET'])
def get_settings():
    """获取当前设置"""
    settings = get_all_settings()
    return jsonify({'success': True, 'user_name': settings.get('user_name', ''),
                    'student_id': settings.get('student_id', '')})