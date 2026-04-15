#!/usr/bin/env python3
import time
import threading
from tomato_clock import TomatoClock, TomatoState

def test_auto_switch():
    print("测试番茄钟自动切换功能...")
    
    # 创建番茄钟，设置很短的时间便于测试
    tc = TomatoClock(work_minutes=0.1, break_minutes=0.05)  # 6秒工作，3秒休息
    
    # 记录状态变化
    states = []
    def on_state_change(state, remaining_time):
        states.append((state, remaining_time))
        print(f"状态变化: {state.value}, 剩余时间: {remaining_time}")
    
    def on_phase_complete(state):
        print(f"阶段完成: {state.value}")
    
    tc.on_state_change = on_state_change
    tc.on_phase_complete = on_phase_complete
    
    print("开始工作...")
    tc.start_work()
    
    # 等待足够长的时间观察自动切换
    time.sleep(15)
    
    print(f"记录的状态变化: {len(states)}")
    for state, time_left in states:
        print(f"  {state.value}: {time_left}秒")
    
    print("测试完成!")

if __name__ == "__main__":
    test_auto_switch()