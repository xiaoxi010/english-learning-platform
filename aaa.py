import sqlite3
conn = sqlite3.connect("vocabulary.db")
cursor = conn.cursor()
cursor.execute("DELETE FROM words WHERE group_id IN (SELECT wg.id FROM word_groups wg JOIN dictionaries d ON wg.dict_id = d.id WHERE d.dict_name = 'A-错题词典')")
conn.commit()
print(f"删除了 {cursor.rowcount} 个单词")
conn.close()