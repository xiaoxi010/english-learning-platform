# skill_db_schema.py - 技能数据库表结构（每用户独立库，仅建表不删数据）
import os
import sqlite3

_initialized_paths: set[str] = set()


def ensure_skill_database(db_path: str) -> None:
    """确保技能库表结构存在；已存在的数据不会被清空。"""
    db_path = os.path.abspath(db_path)
    if db_path in _initialized_paths:
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resource_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER,
            uploader TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            file_path TEXT,
            tags TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES question_categories (id),
            UNIQUE(category_id, name)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS single_choice_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            question TEXT NOT NULL,
            question_image TEXT,
            correct_answer TEXT NOT NULL,
            wrong_answer1 TEXT,
            wrong_answer2 TEXT,
            wrong_answer3 TEXT,
            explanation TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS multi_choice_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            question TEXT NOT NULL,
            question_image TEXT,
            correct_answers TEXT,
            answer_options TEXT,
            explanation TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fill_in_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            question TEXT NOT NULL,
            question_image TEXT,
            answer TEXT NOT NULL,
            explanation TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_answer_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            question TEXT NOT NULL,
            question_image TEXT,
            answer TEXT NOT NULL,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            scenario TEXT NOT NULL,
            sub_questions TEXT,
            sub_answers TEXT,
            sub_explanations TEXT,
            explanation TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES question_groups (id)
        )
    ''')

    conn.commit()
    conn.close()
    _initialized_paths.add(db_path)
