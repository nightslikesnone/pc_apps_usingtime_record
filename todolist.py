import sqlite3
from datetime import datetime
from config import DB_PATH

class TodoItem:
    def __init__(self, id=None, title="", completed=False, created_at=None, updated_at=None):
        self.id = id
        self.title = title
        self.completed = completed
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

def get_connection():
    """返回一个新的数据库连接"""
    return sqlite3.connect(DB_PATH)

def init_todolist_table():
    """初始化todolist表"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS todolist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_all_todos():
    """获取所有todo项目"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, title, completed, created_at, updated_at FROM todolist ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    todos = []
    for row in rows:
        todo = TodoItem(
            id=row[0],
            title=row[1],
            completed=bool(row[2]),
            created_at=row[3],
            updated_at=row[4]
        )
        todos.append(todo)
    return todos

def add_todo(title):
    """添加新的todo项目"""
    if not title.strip():
        return None
        
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT INTO todolist (title, completed, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    ''', (title.strip(), 0, now, now))
    todo_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return TodoItem(id=todo_id, title=title.strip(), completed=False, created_at=now, updated_at=now)

def update_todo_completed(todo_id, completed):
    """更新todo项目的完成状态"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('UPDATE todolist SET completed = ?, updated_at = ? WHERE id = ?', 
              (int(completed), now, todo_id))
    conn.commit()
    conn.close()

def delete_todo(todo_id):
    """删除todo项目"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM todolist WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()

def update_todo_title(todo_id, title):
    """更新todo项目的标题"""
    if not title.strip():
        return False
        
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('UPDATE todolist SET title = ?, updated_at = ? WHERE id = ?', 
              (title.strip(), now, todo_id))
    conn.commit()
    conn.close()
    return True