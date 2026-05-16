import ctypes
from ctypes import wintypes
import time

# ---------- 鼠标事件标志 ----------
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_ABSOLUTE    = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# ---------- 自修复 ULONG_PTR 定义 ----------
if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_ulonglong
else:
    ULONG_PTR = ctypes.c_ulong

# ---------- 完整的输入结构体定义 ----------
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          wintypes.LONG),
        ("dy",          wintypes.LONG),
        ("mouseData",   wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         wintypes.WORD),
        ("wScan",       wintypes.WORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg",    wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type",  wintypes.DWORD),
        ("input", _INPUT_UNION),
    ]

# ---------- 【核心修复】独立 DLL 实例 + 宽松类型声明 ----------
# 使用 WinDLL 创建独立实例，彻底避开 ctypes.windll 的全局 argtypes 缓存污染
_user32 = ctypes.WinDLL('user32', use_last_error=True)
SendInput = _user32.SendInput
# 第二参数使用 c_void_p，关闭 ctypes 对 LP_INPUT 的严格身份校验
SendInput.argtypes = [wintypes.UINT, ctypes.c_void_p, ctypes.c_int]
SendInput.restype  = wintypes.UINT

# ---------- 安全发送函数 ----------
def _send_input(inp: INPUT) -> int:
    """
    安全发送 INPUT 结构体。
    byref() 返回轻量级引用对象，配合 c_void_p 参数类型可完美绕过所有指针类型冲突。
    """
    return SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

# ---------- 辅助函数 ----------
def _make_mouse_input(dx, dy, flags):
    """创建一个正确填充的 INPUT 结构体"""
    inp = INPUT()
    inp.type                = INPUT_MOUSE
    inp.input.mi.dx         = dx
    inp.input.mi.dy         = dy
    inp.input.mi.mouseData  = 0
    inp.input.mi.dwFlags    = flags
    inp.input.mi.time       = 0
    inp.input.mi.dwExtraInfo = 0
    return inp

def _screen_to_absolute(x, y):
    """将屏幕像素坐标转换为绝对坐标 (0~65535)"""
    SM_XVIRTUALSCREEN  = 76
    SM_YVIRTUALSCREEN  = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    vx = _user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = _user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = _user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = _user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    if vw == 0 or vh == 0:
        return 0, 0

    # 微软推荐公式（含四舍五入补偿）
    abs_x = int((x - vx) * 65536 / vw + 65536 / (vw * 2))
    abs_y = int((y - vy) * 65536 / vh + 65536 / (vh * 2))
    abs_x = max(0, min(65535, abs_x))
    abs_y = max(0, min(65535, abs_y))
    return abs_x, abs_y

# ---------- 公共接口 ----------
def move_to(x, y):
    """移动鼠标到屏幕坐标 (x, y)"""
    abs_x, abs_y = _screen_to_absolute(x, y)
    flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    inp = _make_mouse_input(abs_x, abs_y, flags)
    _send_input(inp)

def click(x, y, button='left', delay_down=0.05, delay_up=0.05):
    """点击指定坐标：先移动，再按下，最后释放"""
    abs_x, abs_y = _screen_to_absolute(x, y)
    move_flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK

    # 1. 移动鼠标
    inp_move = _make_mouse_input(abs_x, abs_y, move_flags)
    _send_input(inp_move)
    time.sleep(0.02)

    # 2. 确定按键标志
    if button == 'right':
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag   = MOUSEEVENTF_RIGHTUP
    else:
        down_flag = MOUSEEVENTF_LEFTDOWN
        up_flag   = MOUSEEVENTF_LEFTUP

    # 3. 按下
    inp_down = _make_mouse_input(abs_x, abs_y, move_flags | down_flag)
    _send_input(inp_down)
    time.sleep(delay_down)

    # 4. 释放
    inp_up = _make_mouse_input(abs_x, abs_y, move_flags | up_flag)
    _send_input(inp_up)
    time.sleep(delay_up)