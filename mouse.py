import ctypes
from ctypes import wintypes
import time
import sys

if sys.platform != "win32":
    raise OSError("This module only works on Windows.")

# ============================================================
# Windows User32
# ============================================================

user32 = ctypes.WinDLL("user32", use_last_error=True)

# ============================================================
# 鼠标事件标志
# ============================================================

MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_MIDDLEDOWN  = 0x0020
MOUSEEVENTF_MIDDLEUP    = 0x0040
MOUSEEVENTF_ABSOLUTE    = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# GetSystemMetrics 常量
SM_XVIRTUALSCREEN  = 76
SM_YVIRTUALSCREEN  = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# ============================================================
# ULONG_PTR
# ============================================================

ULONG_PTR = ctypes.c_size_t

# ============================================================
# INPUT 结构体定义
# ============================================================

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


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type",  wintypes.DWORD),
        ("input", INPUT_UNION),
    ]


LPINPUT = ctypes.POINTER(INPUT)

# ============================================================
# WinAPI 函数声明
# ============================================================

SendInput = user32.SendInput
SendInput.argtypes = [
    wintypes.UINT,
    LPINPUT,
    ctypes.c_int,
]
SendInput.restype = wintypes.UINT

GetSystemMetrics = user32.GetSystemMetrics
GetSystemMetrics.argtypes = [ctypes.c_int]
GetSystemMetrics.restype = ctypes.c_int

# ============================================================
# DPI 处理：避免 Windows 缩放导致坐标不准
# ============================================================

def set_dpi_aware():
    """
    尽量让当前进程使用真实屏幕像素坐标。
    如果进程已经设置过 DPI Awareness，Windows 可能拒绝重复设置，忽略即可。
    """
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


set_dpi_aware()

# ============================================================
# 核心发送函数
# ============================================================

def _send_input(*inputs: INPUT) -> int:
    """
    安全调用 SendInput。

    关键点：
    1. 不传 ctypes.addressof(inp) 这种整数地址。
    2. 构造 INPUT 数组。
    3. 把数组转换为 LPINPUT 指针。
    """
    if not inputs:
        return 0

    count = len(inputs)
    input_array_type = INPUT * count
    input_array = input_array_type(*inputs)

    sent = SendInput(
        count,
        ctypes.cast(input_array, LPINPUT),
        ctypes.sizeof(INPUT),
    )

    if sent != count:
        error_code = ctypes.get_last_error()
        raise ctypes.WinError(error_code)

    return sent


# ============================================================
# 辅助函数
# ============================================================

def _make_mouse_input(dx: int, dy: int, flags: int, mouse_data: int = 0) -> INPUT:
    """
    创建鼠标 INPUT 结构体。
    """
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.input.mi.dx = dx
    inp.input.mi.dy = dy
    inp.input.mi.mouseData = mouse_data
    inp.input.mi.dwFlags = flags
    inp.input.mi.time = 0
    inp.input.mi.dwExtraInfo = 0
    return inp


def _get_virtual_screen():
    """
    获取虚拟屏幕区域，支持多显示器和负坐标。
    """
    vx = GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = GetSystemMetrics(SM_CYVIRTUALSCREEN)

    if vw <= 0 or vh <= 0:
        raise RuntimeError("无法获取虚拟屏幕尺寸。")

    return vx, vy, vw, vh


def _screen_to_absolute(x: int, y: int):
    """
    将屏幕像素坐标转换为 SendInput 需要的 0~65535 绝对坐标。
    支持多显示器虚拟桌面。
    """
    vx, vy, vw, vh = _get_virtual_screen()

    # 避免除以 0
    if vw <= 1:
        abs_x = 0
    else:
        abs_x = round((x - vx) * 65535 / (vw - 1))

    if vh <= 1:
        abs_y = 0
    else:
        abs_y = round((y - vy) * 65535 / (vh - 1))

    abs_x = max(0, min(65535, int(abs_x)))
    abs_y = max(0, min(65535, int(abs_y)))

    return abs_x, abs_y


# ============================================================
# 公共接口
# ============================================================

def move_to(x: int, y: int):
    """
    移动鼠标到屏幕坐标 x, y。
    """
    abs_x, abs_y = _screen_to_absolute(x, y)

    flags = (
        MOUSEEVENTF_MOVE
        | MOUSEEVENTF_ABSOLUTE
        | MOUSEEVENTF_VIRTUALDESK
    )

    inp = _make_mouse_input(abs_x, abs_y, flags)
    _send_input(inp)


def click(
    x: int,
    y: int,
    button: str = "left",
    delay_down: float = 0.05,
    delay_up: float = 0.05,
):
    """
    点击指定屏幕坐标。

    button 支持：
    - "left"
    - "right"
    - "middle"
    """
    move_to(x, y)
    time.sleep(0.02)

    button = button.lower()

    if button == "left":
        down_flag = MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_LEFTUP
    elif button == "right":
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP
    elif button == "middle":
        down_flag = MOUSEEVENTF_MIDDLEDOWN
        up_flag = MOUSEEVENTF_MIDDLEUP
    else:
        raise ValueError('button 只能是 "left", "right", 或 "middle"')

    inp_down = _make_mouse_input(0, 0, down_flag)
    _send_input(inp_down)
    time.sleep(delay_down)

    inp_up = _make_mouse_input(0, 0, up_flag)
    _send_input(inp_up)
    time.sleep(delay_up)


def double_click(
    x: int,
    y: int,
    button: str = "left",
    interval: float = 0.08,
):
    """
    双击指定屏幕坐标。
    """
    click(x, y, button=button)
    time.sleep(interval)
    click(x, y, button=button)


def right_click(x: int, y: int):
    """
    右键点击指定屏幕坐标。
    """
    click(x, y, button="right")


def left_click(x: int, y: int):
    """
    左键点击指定屏幕坐标。
    """
    click(x, y, button="left")


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    # 示例：移动到 500, 500 并左键点击
    move_to(500, 500)
    time.sleep(0.5)
    click(500, 500)