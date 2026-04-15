import threading
import flet as ft
from monitor import WindowMonitor
from database import init_db
from gui.main_window import create_flet_app
from tomato_clock import TomatoClock

def main():
    # 初始化数据库
    init_db()

    # 创建监控器
    monitor = WindowMonitor()

    # 创建番茄钟
    tomato_clock = TomatoClock()

    # 启动监控线程（守护线程）
    monitor_thread = threading.Thread(target=monitor.start, daemon=True)
    monitor_thread.start()

    # 获取 Flet 应用主函数
    app_main = create_flet_app(monitor, tomato_clock)

    # 启动 Flet 窗口（阻塞直到窗口关闭）
    # 如果默认视图不显示，可以尝试指定 view=ft.FLET_APP 或 view=ft.WEB_BROWSER 调试
    ft.app(target=app_main)

    # 窗口关闭后停止监控
    monitor.stop()
    # 移除 tomato_clock.stop() 调用，避免 session destroyed 错误
    print("程序退出")

if __name__ == "__main__":
    main()