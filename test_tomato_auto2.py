#!/usr/bin/env python3
import time
from tomato_clock import TomatoClock, TomatoState

def test_auto_switch():
    print("测试番茄钟自动切换功能...")
    
    # 创建番茄钟，设置很短的时间便于测试
    tc = TomatoClock(work_minutes=0.1, break_minutes=0.05)  # 6秒工作，3秒休息
    
    # 记录状态变化
    states = []
    phase_completions = []
    
    def on_state_change(state, remaining_time):
        states.append((state, remaining_time))
        print(f"状态变化: {state.value}, 剩余时间: {remaining_time}")
    
    def on_phase_complete(state):
        phase_completions.append(state)
        print(f"阶段完成: {state.value}")
    
    def on_tick(state, remaining_time):
        # 每次tick都打印，便于调试
        if remaining_time % 2 == 0:  # 每2秒打印一次
            print(f"倒计时: {state.value} - {remaining_time}秒")
    
    tc.on_state_change = on_state_change
    tc.on_phase_complete = on_phase_complete
    tc.on_tick = on_tick
    
    print("开始工作...")
    tc.start_work()
    
    # 等待足够长的时间观察自动切换
    start_time = time.time()
    while time.time() - start_time < 12:  # 等待12秒
        time.sleep(0.1)
        if not tc._running and len(phase_completions) >= 2:
            break
    
    print(f"\n最终状态: {tc.state.value}")
    print(f"记录的状态变化: {len(states)}")
    print(f"阶段完成次数: {len(phase_completions)}")
    
    for i, state in enumerate(phase_completions):
        print(f"  阶段 {i+1}: {state.value}")
    
    print("测试完成!")

if __name__ == "__main__":
    test_auto_switch()