import time
import threading
from enum import Enum
from datetime import datetime, timedelta
from flet import Page
from database import get_tomato_cycles, update_tomato_cycles, get_tomato_settings, save_tomato_settings

class TomatoState(Enum):
    WORK = "工作中"
    BREAK = "休息中"
    LONG_BREAK = "长休息中"
    PAUSED = "已暂停"
    STOPPED = "已停止"

class TomatoClock:
    def __init__(self, work_minutes=25, break_minutes=5, long_break_minutes=15, cycles_before_long_break=4):
        # 从数据库加载设置
        settings = get_tomato_settings()
        self.work_duration = settings['work_duration'] * 60  # 转换为秒
        self.break_duration = settings['break_duration'] * 60
        self.long_break_duration = settings['long_break_duration'] * 60
        self.cycles_before_long_break = cycles_before_long_break
        
        self.state = TomatoState.STOPPED
        self.remaining_time = self.work_duration  # 默认从工作时间开始
        self.total_cycles_completed = 0
        self.current_cycle_count = 0  # 当前循环次数
        self.loop_enabled = False  # 新增：循环模式标志
        
        # 回调函数
        self.on_state_change = None  # 参数: state, remaining_time
        self.on_tick = None  # 参数: state, remaining_time
        self.on_cycle_complete = None  # 参数: state, completed_cycles
        
        # 控制变量
        self._running = False
        self._paused = False
        self._thread = None

    def set_durations(self, work_minutes, break_minutes, long_break_minutes=15):
        """设置工作和休息时长（以分钟为单位）"""
        self.work_duration = work_minutes * 60
        self.break_duration = break_minutes * 60
        self.long_break_duration = long_break_minutes * 60
        
        # 保存设置到数据库
        save_tomato_settings(work_minutes, break_minutes, long_break_minutes)
        
        # 如果当前状态是停止，重置剩余时间
        if self.state == TomatoState.STOPPED:
            self.remaining_time = self.work_duration

    def adjust_work_duration(self, delta_minutes):
        """通过增量调整工作时长"""
        new_work_minutes = max(1, (self.work_duration // 60) + delta_minutes)  # 至少1分钟
        self.work_duration = new_work_minutes * 60
        if self.state == TomatoState.STOPPED:
            self.remaining_time = self.work_duration

    def adjust_break_duration(self, delta_minutes):
        """通过增量调整休息时长"""
        new_break_minutes = max(1, (self.break_duration // 60) + delta_minutes)  # 至少1分钟
        self.break_duration = new_break_minutes * 60

    def start_work(self):
        """开始工作倒计时"""
        if self.state == TomatoState.STOPPED or self.state == TomatoState.PAUSED:
            self.state = TomatoState.WORK
            self.remaining_time = self.work_duration
        self._start_timer()

    def start_break(self):
        """开始休息倒计时"""
        if self.current_cycle_count >= self.cycles_before_long_break:
            # 长休息
            self.state = TomatoState.LONG_BREAK
            self.remaining_time = self.long_break_duration
        else:
            # 普通休息
            self.state = TomatoState.BREAK
            self.remaining_time = self.break_duration
        self._start_timer()

    def _start_timer(self):
        """内部方法：启动计时器线程"""
        if self._thread and self._thread.is_alive():
            self._paused = False
            return
        
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._run_timer, daemon=True)
        self._thread.start()

    def _run_timer(self):
        """内部方法：执行倒计时逻辑"""
        last_update = time.time()
        
        while self._running and self.remaining_time > 0:
            if self._paused:
                time.sleep(0.1)
                continue
            
            current_time = time.time()
            elapsed = int(current_time - last_update)
            
            if elapsed >= 1:  # 每秒更新一次
                self.remaining_time -= elapsed
                last_update = current_time
                
                if self.on_tick:
                    self.on_tick(self.state, self.remaining_time)
                
                # 确保剩余时间不小于0
                if self.remaining_time <= 0:
                    self.remaining_time = 0
                    break
            
            time.sleep(0.1)
        
        # 计时结束，处理状态转换
        if self._running and self.remaining_time <= 0:
            self._handle_completion()

    def _handle_completion(self):
        """处理计时完成的逻辑"""
        if self.state == TomatoState.WORK:
            # 工作完成，进入休息
            self.total_cycles_completed += 1
            self.current_cycle_count += 1
            
            # 保存今天的完成周期数到数据库
            today_str = datetime.now().strftime('%Y-%m-%d')
            update_tomato_cycles(today_str, self.total_cycles_completed)
            
            # 通知周期完成
            if self.on_cycle_complete:
                self.on_cycle_complete(self.state, self.total_cycles_completed)
            
            # 如果启用了循环模式，自动进入休息，否则停止
            if self.loop_enabled:
                self.start_break()
            else:
                # 非循环模式下，只进行一轮工作后停止
                self.stop()
        elif self.state == TomatoState.BREAK or self.state == TomatoState.LONG_BREAK:
            # 休息完成，如果启用了循环模式，则继续工作
            if self.loop_enabled:
                # 检查是否需要长休息
                if self.current_cycle_count >= self.cycles_before_long_break:
                    # 长休息后重置循环计数
                    self.current_cycle_count = 0
                
                # 继续下一轮工作
                self.start_work()
            else:
                # 非循环模式下，休息后停止
                self.stop()

    def pause(self):
        """暂停倒计时"""
        self._paused = True
        self.state = TomatoState.PAUSED
        if self.on_state_change:
            self.on_state_change(self.state, self.remaining_time)

    def resume(self):
        """恢复倒计时"""
        if self.state == TomatoState.PAUSED:
            self._paused = False
            self.state = TomatoState.WORK if self.remaining_time <= self.work_duration else TomatoState.BREAK
            self._start_timer()
            if self.on_state_change:
                self.on_state_change(self.state, self.remaining_time)

    def stop(self):
        """停止倒计时并重置"""
        self._running = False
        self.state = TomatoState.STOPPED
        self.remaining_time = self.work_duration
        self.current_cycle_count = 0
        if self.on_state_change:
            self.on_state_change(self.state, self.remaining_time)

    def reset(self):
        """重置倒计时"""
        self.stop()

    def get_formatted_time(self):
        """获取格式化的时间字符串 MM:SS"""
        minutes = int(self.remaining_time // 60)
        seconds = int(self.remaining_time % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def get_state_info(self):
        """获取当前状态信息"""
        return {
            'state': self.state,
            'remaining_time': self.remaining_time,
            'formatted_time': self.get_formatted_time(),
            'total_cycles_completed': self.total_cycles_completed,
            'current_cycle_count': self.current_cycle_count,
            'work_duration': self.work_duration,
            'break_duration': self.break_duration,
            'long_break_duration': self.long_break_duration
        }

    def enable_loop(self, enabled: bool):
        """启用或禁用循环模式"""
        self.loop_enabled = enabled