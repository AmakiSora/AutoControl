import ctypes
from ctypes import wintypes
import time

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
INPUT_MOUSE = 0


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("input", _INPUT_UNION),
    ]


def _make_mouse_input(dx, dy, flags):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.input.mi.dx = dx
    inp.input.mi.dy = dy
    inp.input.mi.mouseData = 0
    inp.input.mi.dwFlags = flags
    inp.input.mi.time = 0
    inp.input.mi.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    return inp


def _screen_to_absolute(x, y):
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    if vw == 0 or vh == 0:
        return 0, 0

    abs_x = int((x - vx) * 65536 / vw + 65536 / vw / 2)
    abs_y = int((y - vy) * 65536 / vh + 65536 / vh / 2)
    abs_x = max(0, min(65535, abs_x))
    abs_y = max(0, min(65535, abs_y))
    return abs_x, abs_y


def move_to(x, y):
    abs_x, abs_y = _screen_to_absolute(x, y)
    move_flag = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    inp = _make_mouse_input(abs_x, abs_y, move_flag)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def click(x, y, button='left', delay_down=0.05, delay_up=0.05):
    abs_x, abs_y = _screen_to_absolute(x, y)
    move_flag = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK

    inp_move = _make_mouse_input(abs_x, abs_y, move_flag)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_move), ctypes.sizeof(INPUT))
    time.sleep(0.02)

    if button == 'right':
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP
    else:
        down_flag = MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_LEFTUP

    inp_down = _make_mouse_input(abs_x, abs_y, move_flag | down_flag)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
    time.sleep(delay_down)

    inp_up = _make_mouse_input(abs_x, abs_y, move_flag | up_flag)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
    time.sleep(delay_up)
