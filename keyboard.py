import ctypes
from ctypes import wintypes
import time

# -----------------------------
# 常量定义
# -----------------------------
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004
MAPVK_VK_TO_VSC = 0

# -----------------------------
# 虚拟键码表
# -----------------------------
VK_CODES = {
    # 字母 A-Z
    **{chr(i): i for i in range(0x41, 0x5B)},
    # 数字 0-9
    **{str(i): 0x30 + i for i in range(0, 10)},
    # 修饰键
    'ctrl': 0xA2, 'control': 0xA2,
    'alt': 0xA4,
    'altgr': 0xA5,
    'shift': 0xA0,
    'win': 0x5B,
    # 功能键 F1-F12
    **{f'f{i}': 0x6F + i for i in range(1, 13)},
    # 常用特殊键
    'enter': 0x0D, 'return': 0x0D,
    'esc': 0x1B, 'escape': 0x1B,
    'tab': 0x09,
    'backspace': 0x08, 'delete': 0x2E, 'del': 0x2E,
    'insert': 0x2D, 'ins': 0x2D,
    'space': 0x20, ' ': 0x20,
    'up': 0x26, 'down': 0x28,
    'left': 0x25, 'right': 0x27,
    'home': 0x24, 'end': 0x23,
    'pageup': 0x21, 'pgup': 0x21,
    'pagedown': 0x22, 'pgdn': 0x22,
    'capslock': 0x14,
    'numlock': 0x90,
    'scrolllock': 0x91,
    'printscreen': 0x2C, 'prtsc': 0x2C,
    # 小键盘
    'numpad0': 0x60, 'numpad1': 0x61,
    'numpad2': 0x62, 'numpad3': 0x63,
    'numpad4': 0x64, 'numpad5': 0x65,
    'numpad6': 0x66, 'numpad7': 0x67,
    'numpad8': 0x68, 'numpad9': 0x69,
    'numpad_add': 0x6B, 'numpad_subtract': 0x6D,
    'numpad_multiply': 0x6A, 'numpad_divide': 0x6F,
}

# -----------------------------
# ctypes 结构体定义 (完全匹配 Windows API)
# -----------------------------
# 长指针类型
ULONG_PTR = wintypes.WPARAM  # 等价于 ctypes.c_ulonglong (64位) 或 ctypes.c_ulong (32位)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION),
    ]

# 验证结构体大小 (可选，可以注释掉)
# print("MOUSEINPUT size:", ctypes.sizeof(MOUSEINPUT))   # 应为 32 (64位) 或 24 (32位)
# print("KEYBDINPUT size:", ctypes.sizeof(KEYBDINPUT))   # 应为 24 (64位) 或 16 (32位)
# print("INPUT size:", ctypes.sizeof(INPUT))             # 应为 40 (64位) 或 28 (32位)

# 设置 SendInput 签名
ctypes.windll.user32.SendInput.argtypes = [
    wintypes.UINT,           # cInputs
    ctypes.POINTER(INPUT),   # pInputs
    ctypes.c_int,            # cbSize
]
ctypes.windll.user32.SendInput.restype = wintypes.UINT

# -----------------------------
# 内部函数
# -----------------------------
def _make_key_input(vk_code, flags=0):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk_code
    inp.ki.wScan = 0
    inp.ki.dwFlags = flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = 0
    return inp

def _make_unicode_input(char, flags=0):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = 0
    inp.ki.wScan = ord(char)  # Unicode 字符的 UTF-16 代码单元
    inp.ki.dwFlags = KEYEVENTF_UNICODE | flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = 0
    return inp

def _make_scancode_input(vk_code, flags=0):
    scan_code = ctypes.windll.user32.MapVirtualKeyW(vk_code, MAPVK_VK_TO_VSC)
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = 0
    inp.ki.wScan = scan_code
    inp.ki.dwFlags = KEYEVENTF_SCANCODE | flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = 0
    return inp

def _send_input(inp):
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error())

def _get_vk_code(key):
    key_lower = key.lower()
    if key_lower in VK_CODES:
        return VK_CODES[key_lower]
    if len(key) == 1:
        return ord(key.upper())
    return None

# -----------------------------
# 对外函数
# -----------------------------
def press_key(vk_code):
    """按下虚拟键"""
    inp = _make_scancode_input(vk_code)
    _send_input(inp)

def release_key(vk_code):
    """释放虚拟键"""
    inp = _make_scancode_input(vk_code, KEYEVENTF_KEYUP)
    _send_input(inp)

def tap_key(vk_code, duration=0.1):
    """点击虚拟键（按下+释放）"""
    press_key(vk_code)
    time.sleep(duration)
    release_key(vk_code)

def tap_unicode(char, duration=0.05):
    """发送一个 Unicode 字符"""
    _send_input(_make_unicode_input(char))
    time.sleep(duration)
    _send_input(_make_unicode_input(char, KEYEVENTF_KEYUP))

def send_keys(keys, duration=0.1):
    """
    发送键盘输入
    :param keys: 单字符、字符串或按键列表
    :param duration: 每个按键按下时间
    """
    if isinstance(keys, str):
        for char in keys:
            if char == '\n':
                tap_key(VK_CODES['enter'], duration)
            elif char == '\t':
                tap_key(VK_CODES['tab'], duration)
            else:
                tap_unicode(char, duration)
    elif isinstance(keys, list):
        modifiers = []
        regular_keys = []
        for key in keys:
            if key.lower() in ['ctrl', 'control', 'alt', 'shift', 'win', 'altgr']:
                modifiers.append(key.lower())
            else:
                regular_keys.append(key)

        # 按下修饰键
        for mod in modifiers:
            vk = _get_vk_code(mod)
            if vk:
                press_key(vk)
                time.sleep(0.02)

        # 按下普通键
        for key in regular_keys:
            vk = _get_vk_code(key)
            if vk:
                tap_key(vk, duration)

        # 释放修饰键
        for mod in reversed(modifiers):
            vk = _get_vk_code(mod)
            if vk:
                release_key(vk)
                time.sleep(0.02)