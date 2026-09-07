import sqlite3
import datetime

DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT,
            language TEXT,
            latency REAL,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            summary TEXT,
            url TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_search(term, language, latency):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO searches (term, language, latency, timestamp) VALUES (?, ?, ?, ?)", (term, language, latency, time_now))
    conn.commit()
    conn.close()

def save_bookmark(title, summary, url):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO bookmarks (title, summary, url, timestamp) VALUES (?, ?, ?, ?)", (title, summary, url, time_now))
    conn.commit()
    conn.close()

def delete_bookmark(bookmark_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT term, language, latency, timestamp FROM searches ORDER BY id DESC LIMIT 15")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT term, language, latency, timestamp FROM searches ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_bookmarks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, url, timestamp FROM bookmarks ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM searches")
    total_searches = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(latency) FROM searches")
    avg_latency = cursor.fetchone()[0]
    conn.close()
    return {
        "total_searches": total_searches, 
        "avg_latency": round(avg_latency, 2) if avg_latency else 0.0
    }

# Yeh raha wo missing function jo admin panel ko chahiye
def clear_logs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM searches")
    conn.commit()
    conn.close()