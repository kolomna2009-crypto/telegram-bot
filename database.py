import sqlite3
from config import DATABASE_PATH

DEFAULT_CATEGORIES = ["Новости", "Мероприятия", "Развлечения"]
DEFAULT_GREETING = "Я бот для рассылки новостей.\n\nВыбери категории для подписки:"


def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            banned INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE(user_id, category_name)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Migrate: add banned column if missing
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    # Seed default categories if none exist
    cursor.execute('SELECT COUNT(*) FROM categories')
    if cursor.fetchone()[0] == 0:
        for cat in DEFAULT_CATEGORIES:
            cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (cat,))

    # Seed default greeting if missing
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                   ('greeting', DEFAULT_GREETING))

    conn.commit()
    conn.close()
    print("База данных инициализирована")


# ─── Users ────────────────────────────────────────────────────────────────────

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, first_name))
    conn.commit()
    conn.close()


def get_all_users():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE banned = 0')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def ban_user(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def unban_user(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def is_banned(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT banned FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0])


def get_stats():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE banned = 0')
    total_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE banned = 1')
    banned_count = cursor.fetchone()[0]
    cursor.execute('''
        SELECT uc.category_name, COUNT(*)
        FROM user_categories uc
        JOIN users u ON uc.user_id = u.user_id
        WHERE u.banned = 0
        GROUP BY uc.category_name
    ''')
    category_stats = cursor.fetchall()
    conn.close()
    return total_users, banned_count, category_stats


# ─── Categories ───────────────────────────────────────────────────────────────

def get_categories():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM categories ORDER BY name')
    cats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return cats


def add_category_db(name):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (name,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def remove_category_db(name):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_categories WHERE category_name = ?', (name,))
    cursor.execute('DELETE FROM categories WHERE name = ?', (name,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


# ─── User subscriptions ───────────────────────────────────────────────────────

def add_category(user_id, category_name):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO user_categories (user_id, category_name)
        VALUES (?, ?)
    ''', (user_id, category_name))
    conn.commit()
    conn.close()


def remove_category(user_id, category_name):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM user_categories WHERE user_id = ? AND category_name = ?
    ''', (user_id, category_name))
    conn.commit()
    conn.close()


def remove_all_categories(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_categories WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def get_user_categories(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT category_name FROM user_categories WHERE user_id = ?', (user_id,))
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories


def get_users_by_category(category_name):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT uc.user_id
        FROM user_categories uc
        JOIN users u ON uc.user_id = u.user_id
        WHERE uc.category_name = ? AND u.banned = 0
    ''', (category_name,))
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


# ─── Settings ─────────────────────────────────────────────────────────────────

def get_greeting():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'greeting'")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Привет! Выбери категории для подписки:"


def set_greeting(text):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('greeting', ?)", (text,))
    conn.commit()
    conn.close()
