import flet as ft
import win32gui
import win32con
import threading
import time
from datetime import date, timedelta, datetime  # 添加datetime导入
from database import get_today_total, get_today_software_summary, get_tomato_cycles  # 添加get_tomato_cycles导入
from utils import get_icon_for_process, get_friendly_name, get_exe_path_by_process_name
from tomato_clock import TomatoClock
import psutil
import os


def create_flet_app(monitor, tomato_clock=None):
    def main(page: ft.Page):
        page.title = "盒时"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 0
        page.window.width = 700
        page.window.height = 500
        page.window.resizable = False
        page.window.title_bar_hidden = True
        
        # 设置中文字体主题
        page.theme = ft.Theme(font_family="Microsoft YaHei")  # 设置默认字体为微软雅黑
        
        page.update()

        # 异步关闭函数
        async def close_window(_):
            await page.window.close()

        # 标题文字容器（带左边距，expand填充剩余空间）
        title_container = ft.Container(
            content=ft.Text("盒时", size=20, weight="bold", color="black", font_family="Microsoft YaHei"),
            padding=ft.padding.only(left=20),
            expand=True,
        )

        # 可拖拽区域
        drag_area = ft.WindowDragArea(
            content=title_container,
            expand=True,
        )

        # 最小化按钮
        async def minimize_window(_):
            # 获取窗口句柄
            hwnd = win32gui.FindWindow(None, page.title)
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            else:
                print("未找到窗口句柄，无法最小化")

        minimize_btn = ft.Container(
            content=ft.IconButton(
                icon=ft.Icon(ft.Icons.REMOVE, color=ft.Colors.BLACK, size=24),
                width=36,
                height=36,
                style=ft.ButtonStyle(
                    bgcolor={
                        "hovered": "#e0e0e0",
                        "": "#f0f0f0",
                    },
                    shape={
                        "": ft.RoundedRectangleBorder(radius=10),
                        "hovered": ft.RoundedRectangleBorder(radius=10),
                    }
                ),
                on_click=minimize_window,
            ),
            margin=ft.margin.only(left=3),
        )

        # 关闭按钮（整体向左移动约20px）
        close_btn = ft.Container(
            content=ft.IconButton(
                icon=ft.Icon(ft.Icons.CLOSE, color=ft.Colors.BLACK, size=24),
                width=36,
                height=36,
                style=ft.ButtonStyle(
                    bgcolor={
                        "hovered": "#e0e0e0",
                        "": "#f0f0f0",
                    },
                    shape={
                        "": ft.RoundedRectangleBorder(radius=10),
                        "hovered": ft.RoundedRectangleBorder(radius=10),
                    }
                ),
                on_click=close_window,
            ),
            margin=ft.margin.only(right=12),
        )

        # 标题栏行
        title_row = ft.Row(
            [drag_area, minimize_btn, close_btn],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            height=45,
        )

        # 标题栏容器
        title_bar = ft.Container(
            content=title_row,
            bgcolor="#f0f0f0",
            height=45,
        )

        # 当前查看的日期
        current_date = date.today()
        # 获取星期几
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekdays[current_date.weekday()]
        date_text = ft.Text(f"{current_date.strftime('%Y年%m月%d日')} {weekday}", size=16, weight="bold", font_family="Microsoft YaHei")
        
        # 今日累计分左右显示
        total_left = ft.Text("当日总时长", size=20, weight="bold", font_family="Microsoft YaHei")
        total_right = ft.Text("0小时0分钟", size=20, weight="bold", color=ft.Colors.BLUE, font_family="Microsoft YaHei")
        total_row = ft.Row([
            total_left,
            ft.Container(expand=True),
            total_right
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # 番茄钟界面
        tomato_display = ft.Text("25:00", size=60, weight="bold", text_align=ft.TextAlign.CENTER, font_family="Microsoft YaHei")
        tomato_status = ft.Text("未开始", size=16, color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER, font_family="Microsoft YaHei")
        tomato_completed_cycles = ft.Text(f"完成周期: 0", size=14, color=ft.Colors.GREY, font_family="Microsoft YaHei")

        # 番茄钟控制函数（必须是协程函数）
        async def start_tomato(e):
            if tomato_clock:
                tomato_clock.start_work()
        
        async def pause_tomato(e):
            if tomato_clock:
                tomato_clock.pause()
        
        async def reset_tomato(e):
            if tomato_clock:
                tomato_clock.reset()

        # 将按钮居中
        tomato_controls = ft.Row([
            ft.ElevatedButton("开始", icon=ft.Icons.PLAY_ARROW, on_click=start_tomato),
            ft.ElevatedButton("暂停", icon=ft.Icons.PAUSE, on_click=pause_tomato),
            ft.ElevatedButton("重置", icon=ft.Icons.REPLAY, on_click=reset_tomato)
        ], alignment=ft.MainAxisAlignment.CENTER)  # 居中对齐

        # 当前番茄钟设置显示
        current_settings_text = ft.Text("", size=16, weight="bold", font_family="Microsoft YaHei")

        # 通过输入框设置时长的控件
        work_minutes_input = ft.TextField(
            label="工作时长(分钟)",
            value="25",
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        break_minutes_input = ft.TextField(
            label="休息时长(分钟)", 
            value="5",
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # 更新番茄钟时长的函数
        def update_tomato_duration(e):
            try:
                work_minutes = int(work_minutes_input.value)
                break_minutes = int(break_minutes_input.value)
                
                if work_minutes > 0 and break_minutes > 0:
                    if tomato_clock:
                        tomato_clock.set_durations(work_minutes, break_minutes)
                        current_settings_text.value = f"当前设置：工作{work_minutes}分钟，休息{break_minutes}分钟"
                        page.update()
                else:
                    # 输入值无效，提示用户
                    page.snack_bar = ft.SnackBar(ft.Text("请输入大于0的数字"))
                    page.snack_bar.open = True
                    page.update()
            except ValueError:
                # 输入不是有效数字，提示用户
                page.snack_bar = ft.SnackBar(ft.Text("请输入有效的数字"))
                page.snack_bar.open = True
                page.update()

        # 设置当前设置显示的初始值
        if tomato_clock:
            info = tomato_clock.get_state_info()
            work_mins = info['work_duration'] // 60
            break_mins = info['break_duration'] // 60
            work_minutes_input.value = str(work_mins)
            break_minutes_input.value = str(break_mins)
            current_settings_text.value = f"当前设置：工作{work_mins}分钟，休息{break_mins}分钟"

        # 自定义时长控件 - 通过输入框设置
        custom_duration_controls = ft.Column([
            current_settings_text,
            ft.Row([work_minutes_input, break_minutes_input], alignment=ft.MainAxisAlignment.CENTER),  # 居中对齐
            ft.ElevatedButton("应用设置", on_click=update_tomato_duration, width=150)  # 居中对齐
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)  # 整体居中对齐

        # 番茄钟区域（无边框）
        tomato_section = ft.Container(
            content=ft.Column([
                ft.Text("番茄钟", size=20, weight="bold", font_family="Microsoft YaHei"),
                ft.Container(
                    content=tomato_display,
                    alignment=ft.Alignment(0, 0)  # 居中对齐
                ),
                ft.Container(
                    content=tomato_status,
                    alignment=ft.Alignment(0, 0)  # 居中对齐
                ),
                tomato_controls,  # 包含了循环模式开关的行
                ft.Row([ft.Container(expand=True), tomato_completed_cycles], alignment=ft.MainAxisAlignment.END),  # 完成周期靠右
                ft.Divider(height=20),  # 分隔线
                custom_duration_controls  # 滚轮设置时长控件
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),  # 整个列居中对齐
            padding=20,
            margin=ft.margin.symmetric(vertical=10)
        )


        # 内容区域
        software_list_view = ft.ListView(
            controls=[],
            height=260,
            auto_scroll=False,
            expand=True,
            # 使用正确的滚动条可见性属性
            scroll=ft.ScrollMode.AUTO,  # 自适应滚动模式，使滚动条更细
        )

        # 软件统计区域（无底色）
        software_stats_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    date_text,  # 日期文本放在左边
                    ft.Container(expand=True),  # 扩展容器占用中间空间
                    ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS_NEW, on_click=lambda e: switch_date(e, -1)),  # 左箭头放在右边
                    ft.IconButton(icon=ft.Icons.ARROW_FORWARD_IOS, on_click=lambda e: switch_date(e, 1))  # 右箭头放在最右边
                ], alignment=ft.MainAxisAlignment.START),  # 使用START对齐，让内容从左侧开始排列
                total_row,
                ft.Divider(height=20),
                ft.Container(
                    content=software_list_view,
                    padding=10
                ),
            ]),
            padding=20,
            expand=True,
        )

        # 主内容容器 - 用于切换显示
        main_content = ft.Stack([
            ft.Container(content=tomato_section, visible=False, expand=True),  # 初始为隐藏
            ft.Container(content=software_stats_section, visible=True, expand=True)  # 初始为显示
        ])
        
        # 获取当前可见的容器引用
        tomato_container = main_content.controls[0]
        stats_container = main_content.controls[1]

        # 当前选中的页面状态
        current_page = "stats"  # 默认为统计页面

        # 切换显示内容的函数
        async def show_tomato_page(e):
            nonlocal current_page
            tomato_container.visible = True
            stats_container.visible = False
            current_page = "tomato"
            # 更新按钮样式
            update_button_styles()
            page.update()
        
        async def show_stats_page(e):
            nonlocal current_page
            tomato_container.visible = False
            stats_container.visible = True
            current_page = "stats"
            update_button_styles()
            update_data_once()  # 刷新统计数据
            page.update()

        # 更新按钮样式
        def update_button_styles():
            # 更新番茄钟按钮样式
            tomato_btn.style = ft.ButtonStyle(
                bgcolor={"": "#b3d9ff" if current_page == "tomato" else "#f0f0f0", "hovered": "#e0e0e0"},
                shape={"": ft.RoundedRectangleBorder(radius=8)},
                side={"": ft.BorderSide(1, "#d0d0d0")},
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                color={"": ft.Colors.BLACK, "hovered": ft.Colors.BLACK}  # 设置文字颜色为黑色，包括悬停状态
            )
            # 更新时间按钮样式
            stats_btn.style = ft.ButtonStyle(
                bgcolor={"": "#b3d9ff" if current_page == "stats" else "#f0f0f0", "hovered": "#e0e0e0"},
                shape={"": ft.RoundedRectangleBorder(radius=8)},
                side={"": ft.BorderSide(1, "#d0d0d0")},
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                color={"": ft.Colors.BLACK, "hovered": ft.Colors.BLACK}  # 设置文字颜色为黑色，包括悬停状态
            )
            page.update()

        # 日期切换函数（同步版本）
        def switch_date(e, offset):
            nonlocal current_date
            current_date += timedelta(days=offset)
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            weekday = weekdays[current_date.weekday()]
            date_text.value = f"{current_date.strftime('%Y年%m月%d日')} {weekday}"
            update_data_once()  # 立即刷新数据，而不是使用异步线程
            page.update()  # 立即更新页面以显示新日期

        # 左侧边栏 - 与标题栏同色
        # 定义按钮以便稍后更新
        tomato_btn = ft.ElevatedButton(
            "番茄钟",
            icon=ft.Icons.TIMER,
            icon_color=ft.Colors.BLACK,  # 设置图标颜色为黑色
            on_click=show_tomato_page,
            style=ft.ButtonStyle(
                bgcolor={"": "#b3d9ff" if current_page == "tomato" else "#f0f0f0", "hovered": "#e0e0e0"},
                shape={"": ft.RoundedRectangleBorder(radius=8)},
                side={"": ft.BorderSide(1, "#d0d0d0")},
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                color={"": ft.Colors.BLACK, "hovered": ft.Colors.BLACK}  # 设置文字颜色为黑色，包括悬停状态
            ),
            height=50,
            width=120
        )

        stats_btn = ft.ElevatedButton(
            "时间",  # 按钮文本改为"时间"
            icon=ft.Icons.ANALYTICS,
            icon_color=ft.Colors.BLACK,  # 设置图标颜色为黑色
            on_click=show_stats_page,
            style=ft.ButtonStyle(
                bgcolor={"": "#b3d9ff" if current_page == "stats" else "#f0f0f0", "hovered": "#e0e0e0"},
                shape={"": ft.RoundedRectangleBorder(radius=8)},
                side={"": ft.BorderSide(1, "#d0d0d0")},
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                color={"": ft.Colors.BLACK, "hovered": ft.Colors.BLACK}  # 设置文字颜色为黑色，包括悬停状态
            ),
            height=50,
            width=120
        )

        sidebar = ft.Container(
            content=ft.Column([
                stats_btn,  # 时间按钮在上
                tomato_btn  # 番茄钟按钮在下
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15),
            padding=20,
            width=160,
            bgcolor="#f0f0f0"  # 与标题栏同色
        )

        # 主布局 - 使用Row布局，左边侧边栏和分割线，右边内容
        main_layout = ft.Column([
            title_bar,
            ft.Row([
                sidebar,
                ft.Container(
                    content=ft.Divider(),
                    width=1,
                    height=455,  # 窗口高度500 - 标题栏高度45 = 455
                    bgcolor="#d0d0d0"
                ),  # 竖线分割
                ft.Container(
                    content=main_content,
                    expand=True
                )
            ], spacing=0, expand=True)
        ], spacing=0, expand=True)

        page.add(main_layout)
        page.update()

         # 设置番茄钟回调函数
        if tomato_clock:
            def on_state_change(state, remaining_time):
                # 使用 page.run_task 在UI线程中安全地更新界面
                async def update_ui():
                    tomato_display.value = tomato_clock.get_formatted_time()
                    tomato_status.value = state.value
                    page.update()
                
                # 使用 page.run_task 调度异步任务
                page.run_task(update_ui)
            
            def on_tick(state, remaining_time):
                # 使用 page.run_task 在UI线程中安全地更新界面
                async def update_ui():
                    tomato_display.value = tomato_clock.get_formatted_time()
                    tomato_status.value = state.value  # 确保状态也实时更新
                    page.update()
                
                # 使用 page.run_task 调度异步任务
                page.run_task(update_ui)
                
            def on_cycle_complete(state, completed_cycles):
                # 使用 page.run_task 在UI线程中安全地更新界面
                async def update_ui():
                    tomato_completed_cycles.value = f"完成周期: {completed_cycles}"
                    page.update()
                
                # 使用 page.run_task 调度异步任务
                page.run_task(update_ui)
            
            tomato_clock.on_state_change = on_state_change
            tomato_clock.on_tick = on_tick
            tomato_clock.on_cycle_complete = on_cycle_complete
            
            # 启动时从数据库加载今天已完成的周期数
            today_str = datetime.now().strftime('%Y-%m-%d')
            saved_cycles = get_tomato_cycles(today_str)
            tomato_completed_cycles.value = f"完成周期: {saved_cycles}"

        # 后台数据更新线程
        def update_data():
            while True:
                if stats_container.visible:  # 只有在显示统计页面时才更新
                    update_data_once()
                time.sleep(5)

        def update_data_once():
            try:
                total_sec = get_today_total(current_date)
                hours = int(total_sec // 3600)
                minutes = int((total_sec % 3600) // 60)
                total_right.value = f"{hours}小时{minutes}分钟"
                page.update()  # 更新页面以显示总时间
                
                summary = get_today_software_summary(current_date)
                controls = []
                for item in summary:
                    # 确保数据项格式正确，避免类型错误
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        if len(item) == 3:
                            pid, display_name, secs = item
                            # 确保转换为正确的数据类型
                            try:
                                pid = int(pid) if pid is not None and str(pid).isdigit() else None
                            except (ValueError, TypeError):
                                pid = None
                        else:
                            display_name, secs = item
                            pid = None  # 如果数据库中没有PID，则设为None
                        
                        # 确保secs是数值类型
                        try:
                            secs = float(secs)
                        except (ValueError, TypeError):
                            secs = 0
                        
                        h = int(secs // 3600)
                        m = int((secs % 3600) // 60)
                        s = int(secs % 60)
                        time_str = f"{h:02d}:{m:02d}:{s:02d}"
                        
                        # 获取进程的exe路径以获取图标
                        friendly_name = str(display_name) if display_name else ""
                        
                        # 使用utils.py中的函数获取exe路径
                        exe_path = get_exe_path_by_process_name(str(display_name), pid)
                        
                        # 如果成功获取了exe路径，就尝试获取图标
                        icon_control = ft.Icon(ft.Icons.DESKTOP_WINDOWS, size=20, color=ft.Colors.GREY)
                        if exe_path and os.path.exists(exe_path):
                            icon_path = get_icon_for_process(str(display_name), exe_path)
                            if icon_path and os.path.exists(icon_path):
                                # 使用字符串形式的fit参数
                                icon_control = ft.Image(src=icon_path, width=20, height=20, fit="contain")
                        
                        # 如果有PID，获取友好名称
                        if pid is not None:
                            try:
                                friendly_name = get_friendly_name(str(display_name), pid)
                            except Exception:
                                pass
                        
                        controls.append(
                            ft.ElevatedButton(
                                content=ft.Row([
                                    icon_control,  # 图标放在前面
                                    ft.Text(friendly_name, size=16, color=ft.Colors.BLACK, font_family="Microsoft YaHei"),  # 使用友好名称，并设置字体
                                    ft.Container(expand=True),
                                    ft.Text(time_str, size=16, color=ft.Colors.BLACK, font_family="Microsoft YaHei")
                                ], alignment=ft.MainAxisAlignment.START),  # 改为START对齐以适应图标
                                height=40,
                                style=ft.ButtonStyle(
                                    bgcolor={"": "#ffffff", "hovered": "#f0f0f0"},  # 白色背景
                                    shape={"": ft.RoundedRectangleBorder(radius=8)}
                                ),
                                elevation=0,  # 去除阴影
                                on_click=None  # 后续可添加事件
                            )
                        )
                software_list_view.controls = controls
                page.update()
            except TypeError as e:
                print(f"数据类型错误: {e}")
                # 可能是数据库返回的数据类型有问题，跳过本次更新
                pass
            except Exception as e:
                print(f"更新数据时发生错误: {e}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=update_data, daemon=True).start()

    return main