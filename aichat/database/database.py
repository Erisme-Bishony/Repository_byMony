# database/database.py
import pysqlite3 as sqlite3

def init_db():
    conn = sqlite3.connect('datas/aichat.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            thought TEXT,
            conclusion TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def record_thought(task, thought, conclusion):
    conn = sqlite3.connect('datas/aichat.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO thoughts (task, thought, conclusion)
        VALUES (?, ?, ?)
    ''', (task, thought, conclusion))
    conn.commit()
    conn.close()