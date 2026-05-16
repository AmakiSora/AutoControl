import ctypes
from ctypes import wintypes
import time

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_CODES = {
    # 字母键 A-Z
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
    'z': 0x5A,
    
    # 数字键 0-9
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    
    # 修饰键
    'ctrl': 0xA2, 'alt': 0xA4, 'shift': 0xA0, 'win': 0x5B,
    'control': 0xA2, 'altgr': 0xA5,
    
    # 功能键 F1-F12
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    
    # 特殊键
    'enter': 0x0D, 'return': 0x0D,
    'escape': 0x1B, 'esc': 0x1B,
    'tab': 0x09,
    'backspace': 0x08, 'back': 0x08,
    'delete': 0x2E, 'del': 0x2E,
    'insert': 0x2D, 'ins': 0x2D,
    
    # 方向键
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    
    # 导航键
    'home': 0x24, 'end': 0x23,
    'pageup': 0x21, 'pgup': 0x21,
    'pagedown': 0x22, 'pgdn': 0x22,
    
    # 其他
    'space': 0x20, ' ': 0x20,
    'printscreen': 0x2C, 'prtsc': 0x2C,
    'scrolllock': 0x91, 'numlock': 0x90,
    'capslock': 0x14, 'caps': 0x14,
    
    # 小键盘
    'numpad0': 0x60, 'numpad1': 0x61, 'numpad2': 0x62,
    'numpad3': 0x63, 'numpad4': 0x64, 'numpad5': 0x65,
    'numpad6': 0x66, 'numpad7': 0x67, 'numpad8': 0x68,
    'numpad9': 0x69,
    'numpad_add': 0x6B, 'numpad_subtract': 0x6D,
    'numpad_multiply': 0x6A, 'numpad_divide': 0x6F,
}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("input", _INPUT_UNION),
    ]


def _make_key_input(vk_code, flags=0):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.input.ki.wVk = vk_code
    inp.input.ki.wScan = 0
    inp.input.ki.dwFlags = flags
    inp.input.ki.time = 0
    inp.input.ki.dwExtraInfo = ctypes.pointer(wintypes.ULONG(0))
    return inp


def press_key(vk_code):
    """发送按键按下事件"""
    inp = _make_key_input(vk_code)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def release_key(vk_code):
    """发送按键释放事件"""
    inp = _make_key_input(vk_code, KEYEVENTF_KEYUP)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def tap_key(vk_code, duration=0.1):
    """发送完整的按键事件（按下 + 等待 + 释放）"""
    press_key(vk_code)
    time.sleep(duration)
    release_key(vk_code)


def _get_vk_code(key):
    """获取键的虚拟键码"""
    key_lower = key.lower()
    if key_lower in VK_CODES:
        return VK_CODES[key_lower]
    
    if len(key) == 1:
        return wintypes.WORD(ord(key.upper()))
    
    return None


def send_keys(keys, duration=0.1):
    """
    发送键盘输入
    
    :param keys: 单个字符、字符串或按键列表
    :param duration: 每个按键的持续时间（秒）
    """
    if isinstance(keys, str):
        if len(keys) == 1:
            vk = _get_vk_code(keys)
            if vk:
                tap_key(vk, duration)
        else:
            for char in keys:
                vk = _get_vk_code(char)
                if vk:
                    tap_key(vk, duration)
    elif isinstance(keys, list):
        modifiers = []
        regular_keys = []
        
        for key in keys:
            key_lower = key.lower()
            if key_lower in ['ctrl', 'control', 'alt', 'shift', 'win', 'altgr']:
                modifiers.append(key_lower)
            else:
                regular_keys.append(key)
        
        for mod in modifiers:
            vk = _get_vk_code(mod)
            if vk:
                press_key(vk)
                time.sleep(0.05)
        
        for key in regular_keys:
            vk = _get_vk_code(key)
            if vk:
                tap_key(vk, duration)
        
        for mod in reversed(modifiers):
            vk = _get_vk_code(mod)
            if vk:
                release_key(vk)
                time.sleep(0.05)
