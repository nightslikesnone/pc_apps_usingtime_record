# utils.py
import ctypes
from ctypes import wintypes
import win32api
import psutil
import os
from PIL import Image, ImageTk
import win32gui
import win32con
import win32ui
from io import BytesIO
import tempfile

# 定义 SHGFI 常量
SHGFI_ICON = 0x000000100
SHGFI_SMALLICON = 0x000000001

class SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", ctypes.c_ulong),
        ("szDisplayName", wintypes.CHAR * 260),
        ("szTypeName", wintypes.CHAR * 80)
    ]

# 修改缓存字典，使用进程名作为键
_icon_cache = {}

def get_icon_for_process(process_name, exe_path):
    # 使用进程名作为缓存键，而不是exe_path
    cache_key = process_name
    
    if cache_key in _icon_cache:
        cached_path = _icon_cache[cache_key]
        # 检查缓存的文件是否仍然存在
        if os.path.exists(cached_path):
            return cached_path
        else:
            # 如果文件不存在，从缓存中移除
            del _icon_cache[cache_key]
    
    # 如果exe_path不存在，尝试从已知位置查找
    if exe_path is None or not os.path.exists(exe_path):
        # 尝试从系统路径或其他常见位置查找
        possible_paths = [
            f"C:\\Program Files\\{process_name}",
            f"C:\\Program Files (x86)\\{process_name}",
            f"C:\\Windows\\System32\\{process_name}"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                exe_path = path
                break
        
        # 如果还是找不到，返回None
        if exe_path is None or not os.path.exists(exe_path):
            return None

    try:
        shfi = SHFILEINFO()
        ret = ctypes.windll.shell32.SHGetFileInfoW(
            exe_path,
            0,
            ctypes.byref(shfi),
            ctypes.sizeof(shfi),
            SHGFI_ICON | SHGFI_SMALLICON
        )
        if ret == 0 or shfi.hIcon == 0:
            return None

        hIcon = shfi.hIcon

        # 获取图标信息
        icon_info = win32gui.GetIconInfo(hIcon)
        hbmColor = icon_info[4]  # 颜色位图句柄

        # 创建位图对象
        bmp = win32ui.CreateBitmapFromHandle(hbmColor)
        bmp_info = bmp.GetInfo()
        width = bmp_info['bmWidth']
        height = bmp_info['bmHeight']

        # 获取位图数据
        bits = bmp.GetBitmapBits(True)  # 使用位图对象的 GetBitmapBits 方法

        # 转换为 PIL Image
        img = Image.frombuffer('RGBA', (width, height), bits, 'raw', 'BGRA', 0, 1)

        # 销毁图标
        win32gui.DestroyIcon(hIcon)

        # 缩放图标
        img = img.resize((16, 16), Image.LANCZOS)
        
        # 保存到临时文件并返回文件路径，使用进程名作为文件名的一部分
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"icon_{process_name.replace('.', '_').replace(' ', '_')}.png")
        img.save(temp_file_path, 'PNG')
        _icon_cache[cache_key] = temp_file_path
        return temp_file_path  # 返回临时文件路径

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None

def get_exe_path_by_process_name(process_name, pid=None):
    """根据进程名和PID获取可执行文件路径"""
    exe_path = None
    
    # 如果有PID，优先使用PID获取exe路径
    if pid is not None:
        try:
            proc = psutil.Process(pid)
            exe_path = proc.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, ValueError):
            pass
    else:
        # 如果没有PID，尝试通过进程名查找
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                if proc.info['name'] == process_name or process_name in proc.info['name']:
                    exe_path = proc.info['exe']
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
        # 如果仍然没找到exe路径，尝试通过友好名称查找
        if not exe_path:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    proc_name = get_friendly_name(proc.info['name'], proc.info['pid'])
                    if proc_name == process_name or process_name in proc_name:
                        exe_path = proc.info['exe']
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    
    return exe_path

# 空闲检测相关
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT),
                ("dwTime", wintypes.DWORD)]

def get_idle_duration():
    """返回自上次用户输入以来的秒数"""
    li = LASTINPUTINFO()
    li.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
        current_tick = ctypes.windll.kernel32.GetTickCount()
        elapsed_ms = current_tick - li.dwTime
        return elapsed_ms / 1000.0
    return 0

# 友好名称缓存（可以放在函数内部或作为模块级变量）
_description_cache = {}

def get_file_description_from_path(exe_path):
    """从可执行文件路径中获取文件描述"""
    try:
        translation = win32api.GetFileVersionInfo(exe_path, "\\VarFileInfo\\Translation")
        if translation:
            lang, codepage = translation[0]
            str_path = f"\\StringFileInfo\\{lang:04X}{codepage:04X}\\FileDescription"
            desc = win32api.GetFileVersionInfo(exe_path, str_path)
            if desc:
                return desc
    except Exception:
        pass
    return None

def get_friendly_name(process_name, pid):
    """根据进程ID获取友好的显示名称"""
    global _description_cache
    if pid in _description_cache:
        return _description_cache[pid]
    try:
        process = psutil.Process(pid)
        exe_path = process.exe()
        if exe_path:
            desc = get_file_description_from_path(exe_path)
            if desc:
                _description_cache[pid] = desc
                return desc
    except Exception:
        pass
    _description_cache[pid] = process_name
    return process_name