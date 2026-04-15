# database.py
import sqlite3
from datetime import datetime, date
from config import DB_PATH

def get_connection():
    """返回一个新的数据库连接（每个线程应使用独立连接）"""
    return sqlite3.connect(DB_PATH)

def init_db():
    """初始化数据库表结构（创建表、添加列）"""
    conn = get_connection()
    c = conn.cursor()
    # 创建 sessions 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process TEXT,
            friendly_name TEXT,
            start_time REAL,
            end_time REAL
        )
    ''')
    # 添加 is_idle 列（如果不存在）
    try:
        c.execute('ALTER TABLE sessions ADD COLUMN is_idle INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    
    # 创建番茄钟设置表
    c.execute('''
        CREATE TABLE IF NOT EXISTS tomato_settings (
            id INTEGER PRIMARY KEY,
            work_duration INTEGER,
            break_duration INTEGER,
            long_break_duration INTEGER
        )
    ''')
    
    # 创建番茄钟周期记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS tomato_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            completed_cycles INTEGER
        )
    ''')
    
    # 创建 todolist 表
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


def get_tomato_settings():
    """获取番茄钟设置"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT work_duration, break_duration, long_break_duration FROM tomato_settings WHERE id = 1')
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'work_duration': result[0],
            'break_duration': result[1],
            'long_break_duration': result[2]
        }
    else:
        # 默认设置：工作25分钟，休息5分钟，长休息15分钟
        return {
            'work_duration': 25,
            'break_duration': 5,
            'long_break_duration': 15
        }


def save_tomato_settings(work_duration, break_duration, long_break_duration):
    """保存番茄钟设置"""
    conn = get_connection()
    c = conn.cursor()
    
    # 先删除旧设置，再插入新设置
    c.execute('DELETE FROM tomato_settings WHERE id = 1')
    c.execute('''
        INSERT INTO tomato_settings (id, work_duration, break_duration, long_break_duration)
        VALUES (1, ?, ?, ?)
    ''', (work_duration, break_duration, long_break_duration))
    
    conn.commit()
    conn.close()


def get_tomato_cycles(date_str):
    """获取指定日期的番茄钟完成周期数"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT completed_cycles FROM tomato_cycles WHERE date = ?', (date_str,))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else 0


def update_tomato_cycles(date_str, completed_cycles):
    """更新指定日期的番茄钟完成周期数"""
    conn = get_connection()
    c = conn.cursor()
    
    # 检查是否已有记录
    c.execute('SELECT id FROM tomato_cycles WHERE date = ?', (date_str,))
    exists = c.fetchone()
    
    if exists:
        # 更新现有记录
        c.execute('UPDATE tomato_cycles SET completed_cycles = ? WHERE date = ?', 
                  (completed_cycles, date_str))
    else:
        # 插入新记录
        c.execute('INSERT INTO tomato_cycles (date, completed_cycles) VALUES (?, ?)', 
                  (date_str, completed_cycles))
    
    conn.commit()
    conn.close()

def insert_session(process, friendly_name, start_time, end_time, is_idle=0):
    """插入一条会话记录"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO sessions (process, friendly_name, start_time, end_time, is_idle)
        VALUES (?, ?, ?, ?, ?)
    ''', (process, friendly_name, start_time, end_time, is_idle))
    conn.commit()
    conn.close()

def get_today_total(today_date):
    """
    获取指定日期的所有非空闲会话总时长（秒）
    :param today_date: datetime.date 对象，如 date.today()
    :return: 总秒数
    """
    conn = get_connection()
    c = conn.cursor()
    # 将日期转换为当天开始和结束的时间戳（Unix 时间戳）
    start_of_day = datetime.combine(today_date, datetime.min.time()).timestamp()
    end_of_day = datetime.combine(today_date, datetime.max.time()).timestamp()
    
    c.execute('''
        SELECT SUM(end_time - start_time) FROM sessions
        WHERE start_time >= ? AND end_time <= ? AND is_idle = 0
    ''', (start_of_day, end_of_day))
    result = c.fetchone()[0]
    conn.close()
    return result if result else 0

def get_today_software_summary(today_date):
    """
    获取指定日期各软件的非空闲会话总时长
    返回列表，每个元素为 (process, display_name, total_seconds)
    按总秒数降序排列
    """
    conn = get_connection()
    c = conn.cursor()
    start_of_day = datetime.combine(today_date, datetime.min.time()).timestamp()
    end_of_day = datetime.combine(today_date, datetime.max.time()).timestamp()

    c.execute('''
        SELECT 
            process,
            COALESCE(friendly_name, process) as display_name,
            SUM(end_time - start_time) as total
        FROM sessions
        WHERE start_time >= ? AND end_time <= ? AND is_idle = 0
        GROUP BY process
        ORDER BY total DESC
    ''', (start_of_day, end_of_day))
    results = c.fetchall()
    conn.close()
    return results  # 每项为 (process, display_name, total_seconds)

# database.py 添加以下函数
def get_hourly_usage(today_date):
    """
    获取指定日期每小时的累计使用时长（秒）
    返回一个长度为24的列表，索引对应小时（0-23）
    """
    conn = get_connection()
    c = conn.cursor()
    start_of_day = datetime.combine(today_date, datetime.min.time()).timestamp()
    end_of_day = datetime.combine(today_date, datetime.max.time()).timestamp()

    # 初始化长度为24的全0列表
    hourly = [0] * 24

    # 查询所有非空闲会话的起止时间
    c.execute('''
        SELECT start_time, end_time FROM sessions
        WHERE start_time >= ? AND end_time <= ? AND is_idle = 0
    ''', (start_of_day, end_of_day))

    for start, end in c.fetchall():
        # 将会话切分到各个小时
        hour_start = start
        while hour_start < end:
            # 当前小时的下一个整点
            next_hour = ((int(hour_start) // 3600) + 1) * 3600
            segment_end = min(next_hour, end)
            # 计算属于哪个小时（基于 start 时间的小时数）
            hour_index = datetime.fromtimestamp(hour_start).hour
            hourly[hour_index] += (segment_end - hour_start)
            hour_start = segment_end

    conn.close()
    return hourly