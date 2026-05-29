import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import os


class ExamStatsDB:
    """单词组考试统计数据库"""

    def __init__(self, db_path="exam_stats.db", vocab_db_path="vocabulary.db"):
        self.db_path = db_path
        self.vocab_db_path = vocab_db_path
        print(f"考试记录数据库路径: {os.path.abspath(db_path)}")
        print(f"词汇数据库路径: {os.path.abspath(vocab_db_path)}")

        # 各版型的通过分数
        self.pass_scores = {
            "盗宝大师": 46,
            "诡影重重": 45,
            "意言译语": 40,
            "三十六计": 47,
            "七十二变": 47,
            "万圣之夜": 43
        }
        self.full_score = 50  # 满分

        self.init_database()

    def init_database(self):
        """初始化考试统计数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建单词组统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_group_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                dictionary_name TEXT NOT NULL,
                challenge_count INTEGER DEFAULT 0,
                pass_count INTEGER DEFAULT 0,
                highest_score REAL DEFAULT 0,
                gpa REAL DEFAULT 0,
                earliest_pass_time TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_name, dictionary_name)
            )
        ''')

        # 创建详细考核记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                dictionary_name TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                score REAL NOT NULL,
                is_passed BOOLEAN NOT NULL,
                gpa REAL DEFAULT 0,
                exam_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                basic_score REAL,
                shadow_score REAL,
                total_score REAL,
                record_details TEXT
            )
        ''')

        # 检查是否需要添加 gpa 列（兼容旧数据库）
        cursor.execute("PRAGMA table_info(exam_records)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'gpa' not in columns:
            print("正在添加 gpa 列...")
            cursor.execute('ALTER TABLE exam_records ADD COLUMN gpa REAL DEFAULT 0')
            print("gpa 列添加成功")

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_group ON word_group_stats(group_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_dict ON word_group_stats(dictionary_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_time ON exam_records(exam_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_group ON exam_records(group_name)')

        conn.commit()
        conn.close()
        print("数据库初始化完成")

    def calculate_exam_gpa(self, score: float, pattern_name: str, is_passed: bool) -> float:
        """
        计算单次考试的绩点（基于版型）
        绩点=（得分-通过分）/（满分-通过分）*5
        未通过的时候绩点为0
        """
        if not is_passed:
            return 0.0

        pass_score = self.pass_scores.get(pattern_name)
        if pass_score is None:
            pass_score = 50

        gpa = (score - pass_score) / (self.full_score - pass_score) * 5
        return round(max(0, min(gpa, 5)), 2)

    def get_highest_score_gpa(self, group_name: str, dictionary_name: str, pattern_name: str) -> float:
        """获取单词组在指定版型下的最高分绩点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 查找该单词组在该版型下的最高分
        cursor.execute('''
            SELECT MAX(score) FROM exam_records
            WHERE group_name = ? AND dictionary_name = ? AND pattern_name = ? AND is_passed = 1
        ''', (group_name, dictionary_name, pattern_name))

        result = cursor.fetchone()
        conn.close()

        if result and result[0] is not None:
            highest_score = result[0]
            return self.calculate_exam_gpa(highest_score, pattern_name, True)
        return 0.0

    def calculate_pattern_integral(self) -> Dict[str, float]:
        """
        计算版型积分（基于版型pattern_name）
        每次通过：积分 += 该考试的绩点
        每次未通过：积分 -= 3
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        integrals = {
            "盗宝大师": 0,
            "诡影重重": 0,
            "意言译语": 0,
            "三十六计": 0,
            "七十二变": 0,
            "万圣之夜": 0
        }

        cursor.execute('''
            SELECT pattern_name, is_passed, gpa
            FROM exam_records
        ''')

        for row in cursor.fetchall():
            pattern_name = row[0]
            is_passed = bool(row[1])
            gpa = row[2] if row[2] else 0

            if pattern_name in integrals:
                if is_passed:
                    integrals[pattern_name] += gpa
                else:
                    integrals[pattern_name] -= 3
            else:
                integrals[pattern_name] = gpa if is_passed else -3

        conn.close()
        return integrals

    def update_or_create_stats(self, group_name: str, dictionary_name: str,
                               score: float, passed: bool, pattern_name: str = None) -> Dict:
        """更新或创建单词组统计记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 计算本次考试的绩点
        exam_gpa = self.calculate_exam_gpa(score, pattern_name, passed) if pattern_name else 0

        cursor.execute('''
            SELECT challenge_count, pass_count, highest_score, gpa, earliest_pass_time
            FROM word_group_stats
            WHERE group_name = ? AND dictionary_name = ?
        ''', (group_name, dictionary_name))

        existing = cursor.fetchone()

        if existing:
            challenge_count, pass_count, highest_score, current_gpa, earliest_pass_time = existing

            new_challenge_count = challenge_count + 1
            new_pass_count = pass_count + (1 if passed else 0)
            new_highest_score = max(highest_score, score)

            # 绩点：直接从该单词组所有通过记录中取最高绩点
            if new_pass_count > 0:
                cursor.execute('''
                    SELECT MAX(gpa) FROM exam_records
                    WHERE group_name = ? AND dictionary_name = ? AND is_passed = 1
                ''', (group_name, dictionary_name))
                result = cursor.fetchone()
                new_gpa = result[0] if result[0] is not None else 0
            else:
                new_gpa = 0

            new_earliest_pass_time = earliest_pass_time
            if passed and earliest_pass_time is None:
                new_earliest_pass_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute('''
                UPDATE word_group_stats
                SET challenge_count = ?, pass_count = ?, highest_score = ?,
                    gpa = ?, earliest_pass_time = ?, last_updated = ?
                WHERE group_name = ? AND dictionary_name = ?
            ''', (new_challenge_count, new_pass_count, new_highest_score,
                  new_gpa, new_earliest_pass_time, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  group_name, dictionary_name))

            record = {
                'group_name': group_name,
                'dictionary_name': dictionary_name,
                'challenge_count': new_challenge_count,
                'pass_count': new_pass_count,
                'highest_score': new_highest_score,
                'gpa': new_gpa,
                'earliest_pass_time': new_earliest_pass_time
            }
        else:
            new_challenge_count = 1
            new_pass_count = 1 if passed else 0
            new_highest_score = score
            new_gpa = exam_gpa if passed else 0
            new_earliest_pass_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if passed else None

            cursor.execute('''
                INSERT INTO word_group_stats 
                (group_name, dictionary_name, challenge_count, pass_count, 
                 highest_score, gpa, earliest_pass_time, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (group_name, dictionary_name, new_challenge_count, new_pass_count,
                  new_highest_score, new_gpa, new_earliest_pass_time,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            record = {
                'group_name': group_name,
                'dictionary_name': dictionary_name,
                'challenge_count': new_challenge_count,
                'pass_count': new_pass_count,
                'highest_score': new_highest_score,
                'gpa': new_gpa,
                'earliest_pass_time': new_earliest_pass_time
            }

        conn.commit()
        conn.close()
        print(
            f"更新统计记录: {group_name} - 挑战{new_challenge_count}次, 通过{record['pass_count']}次, 绩点{record['gpa']:.2f}")
        return record

    def add_exam_record(self, group_name: str, dictionary_name: str,
                        pattern_name: str, score: float, is_passed: bool,
                        basic_score: float = None, shadow_score: float = None,
                        total_score: float = None, record_details: str = None) -> Dict:
        """添加详细考核记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        exam_gpa = self.calculate_exam_gpa(score, pattern_name, is_passed)

        cursor.execute('''
            INSERT INTO exam_records 
            (group_name, dictionary_name, pattern_name, score, is_passed, 
             gpa, exam_time, basic_score, shadow_score, total_score, record_details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (group_name, dictionary_name, pattern_name, score, is_passed,
              exam_gpa,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              basic_score, shadow_score, total_score, record_details))

        record_id = cursor.lastrowid

        cursor.execute('''
            SELECT id, group_name, dictionary_name, pattern_name, score, is_passed,
                   gpa, exam_time, basic_score, shadow_score, total_score, record_details
            FROM exam_records WHERE id = ?
        ''', (record_id,))

        row = cursor.fetchone()
        conn.commit()
        conn.close()

        return {
            'id': row[0],
            'group_name': row[1],
            'dictionary_name': row[2],
            'pattern_name': row[3],
            'score': row[4],
            'is_passed': bool(row[5]),
            'gpa': row[6],
            'exam_time': row[7],
            'basic_score': row[8],
            'shadow_score': row[9],
            'total_score': row[10],
            'record_details': row[11]
        }

    def get_all_stats_with_vocab(self, dictionary_name: str = None) -> List[Dict]:
        """获取所有统计记录（包含词汇数据库中的所有单词组）"""
        vocab_groups = self.get_all_groups_from_vocab()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 用子查询实时获取最高绩点，不依赖word_group_stats表中的旧数据
        cursor.execute('''
            SELECT ws.group_name, ws.dictionary_name, ws.challenge_count, ws.pass_count,
                   ws.highest_score, ws.earliest_pass_time, ws.last_updated,
                   (SELECT MAX(gpa) FROM exam_records 
                    WHERE group_name = ws.group_name 
                    AND dictionary_name = ws.dictionary_name 
                    AND is_passed = 1) as real_gpa
            FROM word_group_stats ws
        ''')

        stats_dict = {}
        for row in cursor.fetchall():
            key = (row[0], row[1])
            stats_dict[key] = {
                'challenge_count': row[2],
                'pass_count': row[3],
                'highest_score': row[4],
                'gpa': row[7] if row[7] is not None else 0,  # 用实时查询的最高绩点
                'earliest_pass_time': row[5],
                'last_updated': row[6]
            }

        conn.close()

        all_records = []
        for group in vocab_groups:
            key = (group['group_name'], group['dictionary_name'])

            if key in stats_dict:
                stats = stats_dict[key]
                all_records.append({
                    'group_name': group['group_name'],
                    'dictionary_name': group['dictionary_name'],
                    'challenge_count': stats['challenge_count'],
                    'pass_count': stats['pass_count'],
                    'highest_score': stats['highest_score'],
                    'gpa': stats['gpa'],
                    'earliest_pass_time': stats['earliest_pass_time']
                })
            else:
                all_records.append({
                    'group_name': group['group_name'],
                    'dictionary_name': group['dictionary_name'],
                    'challenge_count': '-',
                    'pass_count': '-',
                    'highest_score': '-',
                    'gpa': '-',
                    'earliest_pass_time': '-'
                })

        if dictionary_name and dictionary_name != "全部":
            all_records = [r for r in all_records if r['dictionary_name'] == dictionary_name]

        return all_records

    def get_all_exam_records(self, dictionary_name: str = None, limit: int = 500) -> List[Dict]:
        """获取所有详细考核记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if dictionary_name and dictionary_name != "全部":
            cursor.execute('''
                SELECT id, group_name, dictionary_name, pattern_name, score, is_passed,
                       gpa, exam_time, basic_score, shadow_score, total_score, record_details
                FROM exam_records
                WHERE dictionary_name = ?
                ORDER BY exam_time DESC
                LIMIT ?
            ''', (dictionary_name, limit))
        else:
            cursor.execute('''
                SELECT id, group_name, dictionary_name, pattern_name, score, is_passed,
                       gpa, exam_time, basic_score, shadow_score, total_score, record_details
                FROM exam_records
                ORDER BY exam_time DESC
                LIMIT ?
            ''', (limit,))

        records = []
        for row in cursor.fetchall():
            records.append({
                'id': row[0],
                'group_name': row[1],
                'dictionary_name': row[2],
                'pattern_name': row[3],
                'score': row[4],
                'is_passed': bool(row[5]),
                'gpa': row[6],
                'exam_time': row[7],
                'basic_score': row[8],
                'shadow_score': row[9],
                'total_score': row[10],
                'record_details': row[11]
            })

        conn.close()
        return records

    def get_statistics_summary(self) -> Dict:
        """获取统计摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM exam_records')
        total_exams = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM exam_records WHERE is_passed = 1')
        passed_exams = cursor.fetchone()[0] or 0

        total_pass_rate = (passed_exams / total_exams * 100) if total_exams > 0 else 0

        cursor.execute('SELECT AVG(gpa) FROM word_group_stats')
        avg_gpa = cursor.fetchone()[0] or 0

        pattern_integrals = self.calculate_pattern_integral()

        dictionaries = self.get_all_dictionaries_from_vocab()

        return {
            'group_count': self.get_group_count(),
            'total_exams': total_exams,
            'avg_gpa': avg_gpa,
            'total_pass_rate': total_pass_rate,
            'pattern_integrals': pattern_integrals,
            'dict_count': len(dictionaries),
            'total_groups_from_vocab': len(self.get_all_groups_from_vocab())
        }

    def get_group_count(self):
        """获取有考试记录的单词组数量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM word_group_stats')
        count = cursor.fetchone()[0] or 0
        conn.close()
        return count

    def get_dictionaries_list(self) -> List[str]:
        """获取所有词典列表（从词汇数据库）"""
        return self.get_all_dictionaries_from_vocab()

    def get_all_groups_from_vocab(self) -> List[Dict]:
        """从词汇数据库获取所有单词组信息"""
        try:
            if not os.path.exists(self.vocab_db_path):
                print(f"词汇数据库不存在: {self.vocab_db_path}")
                return []

            conn = sqlite3.connect(self.vocab_db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT wg.group_name, d.dict_name, d.id as dict_id
                FROM word_groups wg
                JOIN dictionaries d ON wg.dict_id = d.id
                ORDER BY d.dict_name, wg.group_name
            ''')

            groups = []
            for row in cursor.fetchall():
                groups.append({
                    'group_name': row[0],
                    'dictionary_name': row[1],
                    'dict_id': row[2]
                })

            conn.close()
            print(f"从词汇数据库获取到 {len(groups)} 个单词组")
            return groups
        except Exception as e:
            print(f"读取词汇数据库失败: {e}")
            return []

    def get_all_dictionaries_from_vocab(self) -> List[str]:
        """从词汇数据库获取所有词典名称"""
        try:
            if not os.path.exists(self.vocab_db_path):
                print(f"词汇数据库不存在: {self.vocab_db_path}")
                return []

            conn = sqlite3.connect(self.vocab_db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT dict_name FROM dictionaries ORDER BY dict_name')
            dictionaries = [row[0] for row in cursor.fetchall()]

            conn.close()
            print(f"从词汇数据库获取到 {len(dictionaries)} 个词典: {dictionaries}")
            return dictionaries
        except Exception as e:
            print(f"读取词典失败: {e}")
            return []

    def clear_all_records(self) -> bool:
        """清空所有记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM word_group_stats')
            cursor.execute('DELETE FROM exam_records')
            conn.commit()
            conn.close()
            print("已清空所有记录")
            return True
        except Exception as e:
            print(f"清空记录失败: {e}")
            return False


def get_exam_stats_db():
    """获取当前登录用户的考试统计库（每用户独立，数据持久保存）。"""
    try:
        from flask import has_request_context, session
        if has_request_context():
            user = session.get('user')
            if user and user.get('id'):
                from user_data_paths import get_user_exam_stats_db_path
                from vocabulary_manager import get_vocab_manager
                return ExamStatsDB(
                    get_user_exam_stats_db_path(user['id']),
                    get_vocab_manager().db_path,
                )
    except Exception:
        pass
    return ExamStatsDB()