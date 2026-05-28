# vocabulary_manager.py - 支持用户隔离的词汇管理器
import json
import os
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from openpyxl import Workbook, load_workbook

# 用户词汇库根目录
USER_VOCAB_DIR = "user_vocabularies"

def get_user_db_path(user_id=None):
    """获取用户数据库路径"""
    if user_id:
        os.makedirs(USER_VOCAB_DIR, exist_ok=True)
        return os.path.join(USER_VOCAB_DIR, f"vocabulary_{user_id}.db")
    return "vocabulary.db"

def init_user_vocabulary(user_id):
    """为新用户初始化词汇库"""
    vm = VocabularyManager(user_id=user_id)
    print(f"用户 {user_id} 词汇库初始化完成")
    return True


class VocabularyManager:
    def __init__(self, user_id=None, db_path=None):
        """初始化词汇管理器
        
        Args:
            user_id: 用户ID，用于隔离用户数据
            db_path: 直接指定数据库路径（优先级高于user_id）
        """
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = get_user_db_path(user_id)
        self.current_dictionary = None
        self.init_database()
        self.init_wrong_book_system()

    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建词典表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dictionaries
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dict_name TEXT UNIQUE NOT NULL,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                description TEXT,
                sort_order INTEGER DEFAULT 0
            )
        ''')

        # 创建单词组表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_groups
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                dict_id INTEGER NOT NULL,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                FOREIGN KEY (dict_id) REFERENCES dictionaries(id),
                UNIQUE(group_name, dict_id)
            )
        ''')

        # 创建单词表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS words
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                part_of_speech TEXT NOT NULL,
                chinese_meaning TEXT NOT NULL,
                group_id INTEGER,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                review_count INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES word_groups(id),
                UNIQUE(word, group_id)
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_word ON words(word)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_group_id ON words(group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_group_name ON word_groups(group_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dict_id ON word_groups(dict_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dict_name ON dictionaries(dict_name)')

        # 插入默认词典
        cursor.execute('''
            INSERT OR IGNORE INTO dictionaries (dict_name, description, sort_order) 
            VALUES (?, ?, ?)
        ''', ('默认词典', '系统默认词典', 0))

        # 插入错题词典
        cursor.execute('''
            INSERT OR IGNORE INTO dictionaries (dict_name, description, sort_order, is_active) 
            VALUES (?, ?, ?, ?)
        ''', ('A-错题词典', '系统错题词典，自动管理', -1, 1))

        conn.commit()
        conn.close()
        self._add_sort_order_column()

    def init_wrong_book_system(self):
        """初始化错题本系统（5个错题本）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 确保错题词典存在且激活
            cursor.execute('''
                INSERT OR IGNORE INTO dictionaries (dict_name, description, is_active, sort_order) 
                VALUES (?, ?, 1, -1)
            ''', ('A-错题词典', '系统错题词典，自动管理'))

            cursor.execute('''
                UPDATE dictionaries SET is_active = 1, sort_order = -1 
                WHERE dict_name = 'A-错题词典'
            ''')

            conn.commit()
            conn.close()

            # 创建5个错题本
            for i in range(1, 6):
                group_name = f'A-错题本-{i}'
                self._create_wrong_book_if_not_exists(group_name)

            print(f"错题本系统初始化完成: {self.db_path}")

        except Exception as e:
            print(f"初始化错题本系统失败: {e}")

    def _create_wrong_book_if_not_exists(self, group_name: str) -> bool:
        """创建错题本（如果不存在）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取错题词典的ID
            cursor.execute("SELECT id FROM dictionaries WHERE dict_name = 'A-错题词典'")
            dict_result = cursor.fetchone()
            if not dict_result:
                conn.close()
                return False

            dict_id = dict_result[0]

            # 检查错题本是否已存在
            cursor.execute('''
                SELECT COUNT(*) FROM word_groups 
                WHERE group_name = ? AND dict_id = ?
            ''', (group_name, dict_id))

            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    'INSERT INTO word_groups (group_name, dict_id, description) VALUES (?, ?, ?)',
                    (group_name, dict_id, '系统错题本，自动管理')
                )
                conn.commit()

            conn.close()
            return True
        except Exception as e:
            print(f"创建错题本失败: {e}")
            return False

    def _add_sort_order_column(self):
        """检查并添加 sort_order 列"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(dictionaries)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'sort_order' not in columns:
                cursor.execute('ALTER TABLE dictionaries ADD COLUMN sort_order INTEGER DEFAULT 0')
                cursor.execute('SELECT id FROM dictionaries ORDER BY created_time')
                rows = cursor.fetchall()
                for order, row in enumerate(rows):
                    cursor.execute('UPDATE dictionaries SET sort_order = ? WHERE id = ?', (order, row[0]))
                conn.commit()

            conn.close()
        except Exception as e:
            print(f"添加 sort_order 列失败: {e}")

    def update_dictionary_order(self, dict_names: List[str]) -> bool:
        """更新词典顺序"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for order, dict_name in enumerate(dict_names):
                cursor.execute('UPDATE dictionaries SET sort_order = ? WHERE dict_name = ?', (order, dict_name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"更新词典顺序失败: {e}")
            return False

    def get_dictionaries_ordered(self) -> List[Dict]:
        """获取按顺序排列的词典列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, dict_name, created_time, is_active, description, sort_order,
                       (SELECT COUNT(*) FROM word_groups WHERE dict_id = dictionaries.id) as group_count
                FROM dictionaries
                ORDER BY sort_order, created_time DESC
            ''')

            dictionaries = []
            for row in cursor.fetchall():
                dictionaries.append({
                    'id': row[0],
                    'dict_name': row[1],
                    'created_time': row[2],
                    'is_active': bool(row[3]),
                    'description': row[4],
                    'sort_order': row[5],
                    'group_count': row[6]
                })
            conn.close()
            return dictionaries
        except Exception as e:
            print(f"获取有序词典列表失败: {e}")
            return []

    def get_dictionary_status(self) -> Dict[str, bool]:
        """获取所有词典的使用状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT dict_name, is_active FROM dictionaries ORDER BY sort_order')
            status = {}
            for row in cursor.fetchall():
                dict_name = row[0]
                if dict_name == 'A-错题词典':
                    status[dict_name] = True
                else:
                    status[dict_name] = bool(row[1])
            conn.close()
            return status
        except Exception as e:
            print(f"获取词典状态失败: {e}")
            return {}

    def set_dictionary_status(self, dict_name: str, is_active: bool) -> bool:
        """设置词典使用状态"""
        if dict_name == 'A-错题词典':
            return True
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE dictionaries SET is_active = ? WHERE dict_name = ?', (1 if is_active else 0, dict_name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"设置词典状态失败: {e}")
            return False

    def get_active_dictionaries(self) -> List[str]:
        """获取所有被激活的词典名称"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT dict_name FROM dictionaries 
                WHERE is_active = 1 OR dict_name = 'A-错题词典'
                ORDER BY sort_order
            ''')
            active_dicts = [row[0] for row in cursor.fetchall()]
            conn.close()
            return active_dicts
        except Exception as e:
            print(f"获取激活词典失败: {e}")
            return []

    def add_dictionary(self, dict_name: str, description: str = "") -> bool:
        """添加词典"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(sort_order) FROM dictionaries')
            max_order = cursor.fetchone()[0] or 0
            cursor.execute('INSERT INTO dictionaries (dict_name, description, sort_order) VALUES (?, ?, ?)',
                           (dict_name, description, max_order + 1))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"添加词典失败: {e}")
            return False

    def delete_dictionary(self, dict_name: str) -> bool:
        """删除词典"""
        if dict_name in ['默认词典', 'A-错题词典']:
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM dictionaries WHERE dict_name = ?', (dict_name,))
            dict_id_result = cursor.fetchone()
            if not dict_id_result:
                return False
            dict_id = dict_id_result[0]
            cursor.execute('DELETE FROM words WHERE group_id IN (SELECT id FROM word_groups WHERE dict_id = ?)', (dict_id,))
            cursor.execute('DELETE FROM word_groups WHERE dict_id = ?', (dict_id,))
            cursor.execute('DELETE FROM dictionaries WHERE id = ?', (dict_id,))
            conn.commit()
            conn.close()
            if self.current_dictionary == dict_name:
                self.current_dictionary = None
            return True
        except Exception as e:
            print(f"删除词典失败: {e}")
            return False

    def get_all_groups(self, sort_by: str = "name") -> List[Dict]:
        """获取所有激活词典的单词组列表"""
        try:
            active_dicts = self.get_active_dictionaries()
            if not active_dicts:
                return []

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(active_dicts))

            if sort_by == "name":
                cursor.execute(f'''
                    SELECT wg.group_name, wg.created_time, wg.description, 
                           COUNT(w.id) as word_count, d.dict_name
                    FROM word_groups wg
                    JOIN dictionaries d ON wg.dict_id = d.id
                    LEFT JOIN words w ON wg.id = w.group_id
                    WHERE d.dict_name IN ({placeholders})
                    GROUP BY wg.id
                    ORDER BY wg.group_name COLLATE NOCASE
                ''', active_dicts)
            elif sort_by == "date":
                cursor.execute(f'''
                    SELECT wg.group_name, wg.created_time, wg.description, 
                           COUNT(w.id) as word_count, d.dict_name
                    FROM word_groups wg
                    JOIN dictionaries d ON wg.dict_id = d.id
                    LEFT JOIN words w ON wg.id = w.group_id
                    WHERE d.dict_name IN ({placeholders})
                    GROUP BY wg.id
                    ORDER BY wg.id DESC
                ''', active_dicts)
            else:
                cursor.execute(f'''
                    SELECT wg.group_name, wg.created_time, wg.description, 
                           COUNT(w.id) as word_count, d.dict_name
                    FROM word_groups wg
                    JOIN dictionaries d ON wg.dict_id = d.id
                    LEFT JOIN words w ON wg.id = w.group_id
                    WHERE d.dict_name IN ({placeholders})
                    GROUP BY wg.id
                    ORDER BY wg.group_name COLLATE NOCASE
                ''', active_dicts)

            groups = []
            for row in cursor.fetchall():
                groups.append({
                    'group_name': row[0],
                    'created_time': row[1],
                    'description': row[2],
                    'word_count': row[3],
                    'dict_name': row[4]
                })
            conn.close()
            return groups
        except Exception as e:
            print(f"获取单词组列表失败: {e}")
            return []

    def add_word_group(self, group_name: str, words_data: List[Dict], description: str = "",
                       dict_name: str = None) -> bool:
        """添加单词组"""
        try:
            if dict_name is None:
                dict_name = "默认词典"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM dictionaries WHERE dict_name = ?', (dict_name,))
            dict_result = cursor.fetchone()
            if not dict_result:
                conn.close()
                return False
            dict_id = dict_result[0]

            cursor.execute('INSERT OR REPLACE INTO word_groups (group_name, dict_id, description) VALUES (?, ?, ?)',
                           (group_name, dict_id, description))

            cursor.execute('SELECT id FROM word_groups WHERE group_name = ? AND dict_id = ?', (group_name, dict_id))
            group_id = cursor.fetchone()[0]

            for word_data in words_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO words (word, part_of_speech, chinese_meaning, group_id) 
                    VALUES (?, ?, ?, ?)
                ''', (word_data['word'], word_data['part_of_speech'], word_data['chinese_meaning'], group_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"添加单词组失败: {e}")
            return False

    def get_word_group(self, group_name: str, dict_name: str = None) -> Optional[Dict]:
        """获取指定单词组的详细信息"""
        try:
            if dict_name is None:
                dict_name = "默认词典"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT wg.id, wg.group_name, wg.created_time, wg.description, d.dict_name
                FROM word_groups wg
                JOIN dictionaries d ON wg.dict_id = d.id
                WHERE wg.group_name = ? AND d.dict_name = ?
            ''', (group_name, dict_name))

            group_info = cursor.fetchone()
            if not group_info:
                return None

            cursor.execute('''
                SELECT word, part_of_speech, chinese_meaning, review_count, last_reviewed
                FROM words
                WHERE group_id = ?
                ORDER BY word COLLATE NOCASE
            ''', (group_info[0],))

            words = []
            for row in cursor.fetchall():
                words.append({
                    'word': row[0],
                    'part_of_speech': row[1],
                    'chinese_meaning': row[2],
                    'review_count': row[3],
                    'last_reviewed': row[4]
                })

            conn.close()
            return {
                'group_id': group_info[0],
                'group_name': group_info[1],
                'created_time': group_info[2],
                'description': group_info[3],
                'dict_name': group_info[4],
                'words': words,
                'word_count': len(words)
            }
        except Exception as e:
            print(f"获取单词组失败: {e}")
            return None

    def search_words(self, keyword: str, search_by: str = "word") -> List[Dict]:
        """搜索单词（只在激活的词典中搜索）"""
        try:
            active_dicts = self.get_active_dictionaries()
            if not active_dicts:
                return []

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(active_dicts))

            if search_by == "word":
                cursor.execute(f'''
                    SELECT w.word, w.part_of_speech, w.chinese_meaning, wg.group_name, d.dict_name
                    FROM words w
                    JOIN word_groups wg ON w.group_id = wg.id
                    JOIN dictionaries d ON wg.dict_id = d.id
                    WHERE w.word LIKE ? AND d.dict_name IN ({placeholders})
                    ORDER BY w.word COLLATE NOCASE
                ''', (f'%{keyword}%', *active_dicts))
            elif search_by == "meaning":
                cursor.execute(f'''
                    SELECT w.word, w.part_of_speech, w.chinese_meaning, wg.group_name, d.dict_name
                    FROM words w
                    JOIN word_groups wg ON w.group_id = wg.id
                    JOIN dictionaries d ON wg.dict_id = d.id
                    WHERE w.chinese_meaning LIKE ? AND d.dict_name IN ({placeholders})
                    ORDER BY w.word COLLATE NOCASE
                ''', (f'%{keyword}%', *active_dicts))
            else:
                cursor.execute(f'''
                    SELECT w.word, w.part_of_speech, w.chinese_meaning, wg.group_name, d.dict_name
                    FROM words w
                    JOIN word_groups wg ON w.group_id = wg.id
                    JOIN dictionaries d ON wg.dict_id = d.id
                    WHERE (w.word LIKE ? OR w.chinese_meaning LIKE ?) AND d.dict_name IN ({placeholders})
                    ORDER BY w.word COLLATE NOCASE
                ''', (f'%{keyword}%', f'%{keyword}%', *active_dicts))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'word': row[0],
                    'part_of_speech': row[1],
                    'chinese_meaning': row[2],
                    'group_name': row[3],
                    'dict_name': row[4]
                })
            conn.close()
            return results
        except Exception as e:
            print(f"搜索单词失败: {e}")
            return []

    def delete_word_group(self, group_name: str, dict_name: str = None) -> bool:
        """删除单词组"""
        try:
            if dict_name is None:
                dict_name = "默认词典"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT wg.id FROM word_groups wg
                JOIN dictionaries d ON wg.dict_id = d.id
                WHERE wg.group_name = ? AND d.dict_name = ?
            ''', (group_name, dict_name))

            group_result = cursor.fetchone()
            if not group_result:
                conn.close()
                return False

            group_id = group_result[0]
            cursor.execute('DELETE FROM words WHERE group_id = ?', (group_id,))
            cursor.execute('DELETE FROM word_groups WHERE id = ?', (group_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"删除单词组失败: {e}")
            return False

    def get_current_wrong_book(self) -> Optional[str]:
        """获取当前可添加单词的错题本（第一个未满50个单词的）"""
        try:
            for i in range(1, 6):
                group_name = f'A-错题本-{i}'
                group_data = self.get_word_group(group_name, 'A-错题词典')
                if group_data:
                    word_count = len(group_data.get('words', []))
                    if word_count < 50:
                        return group_name
            return None
        except Exception as e:
            print(f"获取当前错题本失败: {e}")
            return None

    def add_word_to_wrong_book(self, word: str, part_of_speech: str, chinese_meaning: str) -> bool:
        """将单词添加到错题本"""
        try:
            current_book = self.get_current_wrong_book()
            if not current_book:
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT wg.id FROM word_groups wg
                JOIN dictionaries d ON wg.dict_id = d.id
                WHERE wg.group_name = ? AND d.dict_name = 'A-错题词典'
            ''', (current_book,))

            result = cursor.fetchone()
            if not result:
                conn.close()
                return False

            group_id = result[0]

            cursor.execute('''
                SELECT w.id FROM words w
                JOIN word_groups wg ON w.group_id = wg.id
                JOIN dictionaries d ON wg.dict_id = d.id
                WHERE w.word = ? AND d.dict_name = 'A-错题词典'
            ''', (word,))

            if cursor.fetchone():
                conn.close()
                return True

            cursor.execute('''
                INSERT INTO words (word, part_of_speech, chinese_meaning, group_id)
                VALUES (?, ?, ?, ?)
            ''', (word, part_of_speech, chinese_meaning, group_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"添加单词到错题本失败: {e}")
            return False

    def remove_word_from_wrong_book(self, word: str) -> bool:
        """从错题本中删除单词"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM words 
                WHERE word = ? AND group_id IN (
                    SELECT wg.id FROM word_groups wg
                    JOIN dictionaries d ON wg.dict_id = d.id
                    WHERE d.dict_name = 'A-错题词典'
                )
            ''', (word,))
            rows_deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return rows_deleted > 0
        except Exception as e:
            print(f"从错题本删除单词失败: {e}")
            return False

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        try:
            active_dicts = self.get_active_dictionaries()
            if not active_dicts:
                return {}

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(active_dicts))

            cursor.execute(f'''
                SELECT COUNT(*) FROM words w
                JOIN word_groups wg ON w.group_id = wg.id
                JOIN dictionaries d ON wg.dict_id = d.id
                WHERE d.dict_name IN ({placeholders})
            ''', active_dicts)
            total_words = cursor.fetchone()[0]

            cursor.execute(f'''
                SELECT COUNT(*) FROM word_groups wg
                JOIN dictionaries d ON wg.dict_id = d.id
                WHERE d.dict_name IN ({placeholders})
            ''', active_dicts)
            total_groups = cursor.fetchone()[0]

            cursor.execute('''
                SELECT dict_name, is_active,
                       (SELECT COUNT(*) FROM word_groups WHERE dict_id = dictionaries.id) as group_count,
                       (SELECT COUNT(*) FROM words w
                        JOIN word_groups wg ON w.group_id = wg.id
                        WHERE wg.dict_id = dictionaries.id) as word_count
                FROM dictionaries
                ORDER BY sort_order
            ''')
            dict_stats = [
                {
                    'dict_name': row[0],
                    'is_active': bool(row[1]),
                    'group_count': row[2],
                    'word_count': row[3]
                }
                for row in cursor.fetchall()
            ]

            conn.close()
            return {
                'total_words': total_words,
                'total_groups': total_groups,
                'dictionary_statistics': dict_stats,
                'active_dictionaries': active_dicts
            }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}

    def export_to_excel(self, file_path: str) -> bool:
        """导出所有词典到Excel文件"""
        try:
            dictionaries = self.get_dictionaries_ordered()
            if not dictionaries:
                return False

            wb = Workbook()
            ws = wb.active
            ws.title = "词汇管理数据库"

            ws.append(["词汇管理数据库", "", ""])
            ws.append(["词典名称", "词组名称", ""])
            ws.append(["英文单词", "词性", "汉译"])

            for dict_info in dictionaries:
                dict_name = dict_info['dict_name']

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT wg.group_name
                    FROM word_groups wg
                    JOIN dictionaries d ON wg.dict_id = d.id
                    WHERE d.dict_name = ?
                    ORDER BY wg.group_name
                ''', (dict_name,))

                groups = cursor.fetchall()

                for group_row in groups:
                    group_name = group_row[0]
                    ws.append(["", dict_name, group_name])

                    cursor.execute('''
                        SELECT w.word, w.part_of_speech, w.chinese_meaning
                        FROM words w
                        JOIN word_groups wg ON w.group_id = wg.id
                        JOIN dictionaries d ON wg.dict_id = d.id
                        WHERE d.dict_name = ? AND wg.group_name = ?
                        ORDER BY w.word
                    ''', (dict_name, group_name))

                    words = cursor.fetchall()

                    for word_row in words:
                        word, pos, meaning = word_row
                        ws.append([word, pos, meaning])

                    ws.append(["", "", ""])

                conn.close()

            wb.save(file_path)
            return True
        except Exception as e:
            print(f"导出到Excel失败: {e}")
            return False

    def import_from_excel(self, file_path: str, dict_name: str = None) -> bool:
        """从Excel文件导入词汇数据库"""
        try:
            wb = load_workbook(file_path, data_only=True)
            ws = wb.active

            current_dict_name = None
            current_group_name = None
            words_data = []
            imported_groups = 0

            for row in ws.iter_rows(min_row=1, values_only=True):
                if all(cell is None for cell in row):
                    continue

                if (row[0] is None or str(row[0]).strip() == "") and row[1]:
                    if words_data and current_group_name and current_dict_name:
                        target_dict = dict_name if dict_name else current_dict_name
                        if self.add_word_group(current_group_name, words_data, "", target_dict):
                            imported_groups += 1
                        words_data = []

                    current_dict_name = str(row[1]).strip()
                    current_group_name = str(row[2]).strip() if row[2] else "未命名组"

                elif row[0] and row[0] != "词汇管理数据库" and row[0] != "英文单词":
                    word = str(row[0]).strip()
                    pos = str(row[1]).strip() if row[1] else ""
                    meaning = str(row[2]).strip() if row[2] else ""

                    if word and meaning:
                        words_data.append({
                            'word': word,
                            'part_of_speech': pos,
                            'chinese_meaning': meaning
                        })

            if words_data and current_group_name and current_dict_name:
                target_dict = dict_name if dict_name else current_dict_name
                if self.add_word_group(current_group_name, words_data, "", target_dict):
                    imported_groups += 1

            wb.close()
            return imported_groups > 0
        except Exception as e:
            print(f"从Excel导入失败: {e}")
            return False