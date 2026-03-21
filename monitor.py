# monitor.py
import time
from datetime import datetime
import win32gui
import win32process
import psutil
from config import IDLE_THRESHOLD, CHECK_INTERVAL
from utils import get_idle_duration, get_friendly_name
from database import insert_session

class WindowMonitor:
    def __init__(self):
        self.running = False
        self.current_process = None
        self.current_friendly = None
        self.start_time = None
        self.idle_mode = False

    def start(self):
        """启动监控循环（应在单独线程中运行）"""
        self.running = True
        while self.running:
            self._monitor_iteration()
            time.sleep(CHECK_INTERVAL)

    def stop(self):
        """停止监控"""
        self.running = False

    def _monitor_iteration(self):
        now = time.time()
        idle_sec = get_idle_duration()

        # 空闲检测逻辑
        if idle_sec > IDLE_THRESHOLD and not self.idle_mode:
            # 进入空闲
            self._enter_idle(now)
        elif (idle_sec <= IDLE_THRESHOLD) and self.idle_mode:
            # 退出空闲
            self._exit_idle(now)

        if not self.idle_mode:
            # 获取当前窗口
            process, friendly = self._get_current_window()
            if process != self.current_process:
                # 切换窗口
                self._switch_window(process, friendly, now)

    def _enter_idle(self, now):
        """进入空闲模式"""
        if self.current_process is not None and self.start_time is not None:
            # 结束当前会话
            insert_session(
                self.current_process,
                self.current_friendly,
                self.start_time,
                now,
                is_idle=0
            )
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 进入空闲，结束 {self.current_friendly} 会话")
        # 开始空闲会话
        self.idle_mode = True
        self.current_process = "Idle"
        self.current_friendly = "空闲"
        self.start_time = now
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 进入空闲模式")

    def _exit_idle(self, now):
        """退出空闲模式"""
        if self.current_process is not None and self.start_time is not None:
            # 结束空闲会话
            insert_session(
                self.current_process,
                self.current_friendly,
                self.start_time,
                now,
                is_idle=1
            )
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 退出空闲，空闲时长 {now - self.start_time:.1f} 秒")
        self.idle_mode = False
        self.current_process = None
        self.current_friendly = None
        self.start_time = None

    def _get_current_window(self):
        """获取当前窗口的进程名和友好名称"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            proc_name = process.name()
            friendly = get_friendly_name(proc_name, pid)
            return proc_name, friendly
        except Exception:
            return None, None

    def _switch_window(self, new_process, new_friendly, now):
        """处理窗口切换"""
        # 结束上一个会话
        if self.current_process is not None and self.start_time is not None:
            insert_session(
                self.current_process,
                self.current_friendly,
                self.start_time,
                now,
                is_idle=0
            )
            duration = now - self.start_time
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.current_friendly} 使用了 {duration:.1f} 秒")
        # 开始新会话
        self.current_process = new_process
        self.current_friendly = new_friendly
        self.start_time = now