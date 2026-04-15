#!/usr/bin/env python3
import time
from tomato_clock import TomatoClock, TomatoState

def test_auto_switch():
    print("测试番茄钟自动切换功能...")
    
    # 创建番茄钟，使用数据库中的设置（当前是1分钟工作，1分钟休息）
    tc = TomatoClock()
    
    print(f"工作时长: {tc.work_duration//60}分钟, 休息时长: {tc.break_duration//60}分钟")
    
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
        # 每次tick都打印剩余时间
        if remaining_time % 10 == 0:  # 每10秒打印一次
            print(f"倒计时: {state.value} - {remaining_time}秒")
    
    tc.on_state_change = on_state_change
    tc.on_phase_complete = on_phase_complete
    tc.on_tick = on_tick
    
    print("开始工作...")
    tc.start_work()
    
    # 等待足够长的时间观察自动切换（3分钟）
    start_time = time.time()
    while time.time() - start_time < 180:  # 等待3分钟
        time.sleep(1)
        if len(phase_completions) >= 2:
            print("检测到两次阶段完成，测试成功！")
            break
        if not tc._running:
            print("计时器已停止")
            break
    
    print(f"\n最终状态: {tc.state.value}")
    print(f"记录的状态变化: {len(states)}")
    print(f"阶段完成次数: {len(phase_completions)}")
    
    for i, state in enumerate(phase_completions):
        print(f"  阶段 {i+1}: {state.value}")
    
    print("测试完成!")

if __name__ == "__main__":
    test_auto_switch()