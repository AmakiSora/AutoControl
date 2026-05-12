#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多显示器屏幕监控与图像识别点击工具
使用 mss 进行截图，OpenCV 进行图像匹配
"""

import time
import sys
import os

try:
    import mss
    import mss.tools
    import cv2
    import numpy as np
    import pydirectinput
except ImportError as e:
    print(f"缺少依赖库: {e}")
    print("请安装: pip install mss opencv-python numpy pydirectinput")
    sys.exit(1)

import ctypes
from ctypes import wintypes

# ========== Win32 SendInput 硬件级鼠标控制 ==========
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_ABSOLUTE    = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
INPUT_MOUSE = 0


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          wintypes.LONG),
        ("dy",          wintypes.LONG),
        ("mouseData",   wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
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
    """构造一个 MOUSEINPUT 结构体"""
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
    """将屏幕坐标转换为 SendInput 的绝对坐标 (0-65536 映射到虚拟桌面)"""
    SM_XVIRTUALSCREEN  = 76
    SM_YVIRTUALSCREEN  = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    if vw == 0 or vh == 0:
        return 0, 0

    # 映射到 0-65535 归一化坐标
    abs_x = int((x - vx) * 65536 / vw + 65536 / vw / 2)
    abs_y = int((y - vy) * 65536 / vh + 65536 / vh / 2)
    abs_x = max(0, min(65535, abs_x))
    abs_y = max(0, min(65535, abs_y))
    return abs_x, abs_y


def sendinput_click(x, y, delay_down=0.05, delay_up=0.05):
    """
    使用 Win32 SendInput API 进行硬件级鼠标移动+点击
    这是纯软件层面最底层的方式，游戏也无法区分
    """
    abs_x, abs_y = _screen_to_absolute(x, y)
    move_flag = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK

    # 1) 移动到目标位置
    inp_move = _make_mouse_input(abs_x, abs_y, move_flag)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_move), ctypes.sizeof(INPUT))
    time.sleep(0.02)

    # 2) 鼠标左键按下
    inp_down = _make_mouse_input(abs_x, abs_y, move_flag | MOUSEEVENTF_LEFTDOWN)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
    time.sleep(delay_down)

    # 3) 鼠标左键抬起
    inp_up = _make_mouse_input(abs_x, abs_y, move_flag | MOUSEEVENTF_LEFTUP)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
    time.sleep(delay_up)

    print(f"  SendInput 点击: 屏幕({x},{y}) → 绝对({abs_x},{abs_y})")


def get_monitors():
    """获取所有显示器信息"""
    with mss.mss() as sct:
        monitors = sct.monitors
        # monitors[0] 是所有显示器的并集，monitors[1:] 是各个显示器
        return monitors


def select_monitor(monitors):
    """让用户选择要监控的显示器"""
    print("=" * 60)
    print("检测到以下显示器:")
    print("=" * 60)

    # monitors[0] 是所有显示器的组合，通常不需要
    for i, monitor in enumerate(monitors[1:], start=1):
        print(f"  显示器 {i}:")
        print(f"    左: {monitor['left']}, 上: {monitor['top']}")
        print(f"    宽度: {monitor['width']}, 高度: {monitor['height']}")
        print()

    if len(monitors) == 2:  # 只有1个真实显示器
        print("只有一个显示器，自动选择显示器 1")
        return 1

    while True:
        try:
            choice = int(input(f"请选择要监控的显示器 (1-{len(monitors)-1}): "))
            if 1 <= choice <= len(monitors) - 1:
                return choice
            else:
                print(f"请输入 1 到 {len(monitors)-1} 之间的数字")
        except ValueError:
            print("请输入有效的数字")


def capture_monitor(monitor_index):
    """捕获指定显示器的截图"""
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        screenshot = sct.grab(monitor)

        # 转换为 OpenCV 格式 (BGR)
        img = np.array(screenshot)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        return img_bgr, img_gray, monitor


def load_template(template_path):
    """加载模板图像（支持中文路径）"""
    if not os.path.exists(template_path):
        print(f"错误: 模板图像不存在: {template_path}")
        return None

    # cv2.imread 不支持中文路径，使用 np.fromfile + imdecode 替代
    try:
        file_bytes = np.fromfile(template_path, dtype=np.uint8)
        template = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"错误: 读取模板图像失败: {e}")
        return None

    if template is None:
        print(f"错误: 无法解码模板图像: {template_path}")
        return None

    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    h, w = template_gray.shape

    print(f"模板图像加载成功: {template_path}")
    print(f"模板尺寸: {w}x{h}")
    return template_gray, w, h


def find_template_in_screenshot(screenshot_gray, template_gray, w, h, threshold=0.8):
    """
    在截图中查找模板图像
    返回匹配位置的中心坐标 (相对于截图的坐标)
    """
    # 使用模板匹配
    result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)

    # 获取所有匹配位置
    locations = np.where(result >= threshold)

    # 转换为 (x, y) 坐标列表
    positions = list(zip(*locations[::-1]))  # 交换 x, y

    if len(positions) == 0:
        return None

    # 使用第一个匹配位置
    x, y = positions[0]
    center_x = x + w // 2
    center_y = y + h // 2

    # 获取匹配度
    match_value = result[locations[0][0], locations[1][0]]

    return {
        'x': x,
        'y': y,
        'center_x': center_x,
        'center_y': center_y,
        'width': w,
        'height': h,
        'confidence': float(match_value)
    }


def click_at_monitor_position(monitor, rel_x, rel_y):
    """
    在显示器坐标系中点击位置
    monitor: mss 显示器信息
    rel_x, rel_y: 相对于显示器左上角的坐标
    """
    # 转换为全局屏幕坐标
    global_x = monitor['left'] + rel_x
    global_y = monitor['top'] + rel_y

    print(f"  全局坐标: ({global_x}, {global_y})")

    # 移动鼠标并点击（使用 pydirectinput 走硬件级输入，游戏可识别）
    pydirectinput.moveTo(global_x, global_y)
    sendinput_click(global_x, global_y)


def main():
    print("=" * 60)
    print("  多显示器屏幕监控与图像识别点击工具")
    print("=" * 60)
    print()

    # 1. 获取显示器列表
    monitors = get_monitors()
    print()

    # 2. 用户选择显示器
    selected_index = select_monitor(monitors)
    selected_monitor = monitors[selected_index]
    print(f"\n已选择显示器 {selected_index}")
    print(f"  区域: 左={selected_monitor['left']}, 上={selected_monitor['top']}, "
          f"宽={selected_monitor['width']}, 高={selected_monitor['height']}")
    print()

    # 3. 获取模板图像路径
    # template_path = input("请输入要匹配的图片路径 (默认: xx.jpg): ").strip()
    # if not template_path:
    #     template_path = "xx.jpg"
    template_path = "C:\\COSMOS\\github\\workScript\\自娱自乐小工具\\搜索.jpg"
    if not os.path.exists(template_path):
        print(f"错误: 文件不存在: {template_path}")
        sys.exit(1)

    # 4. 加载模板图像
    template_result = load_template(template_path)
    if template_result is None:
        sys.exit(1)

    template_gray, template_w, template_h = template_result
    print()

    # 5. 设置匹配阈值
    threshold_input = input("请输入匹配阈值 (0.0-1.0, 默认 0.8): ").strip()
    threshold = 0.8
    if threshold_input:
        try:
            threshold = float(threshold_input)
            threshold = max(0.0, min(1.0, threshold))
        except ValueError:
            print("输入无效，使用默认阈值 0.8")

    print(f"匹配阈值: {threshold}")
    print()

    # 6. 主循环
    print("=" * 60)
    print("开始监控...")
    print("按 Ctrl+C 停止")
    print("=" * 60)
    print()

    iteration = 0

    try:
        while iteration < 4:
            iteration += 1
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 第 {iteration} 次检测...")

            # 捕获显示器截图
            img_bgr, img_gray, monitor = capture_monitor(selected_index)

            # 查找模板
            match_result = find_template_in_screenshot(
                img_gray, template_gray, template_w, template_h, threshold
            )

            if match_result:
                print(f"  ✓ 找到匹配!")
                print(f"    位置: ({match_result['x']}, {match_result['y']})")
                print(f"    中心: ({match_result['center_x']}, {match_result['center_y']})")
                print(f"    置信度: {match_result['confidence']:.2%}")

                # 点击中心位置
                print(f"  正在移动到匹配位置并点击...")
                click_at_monitor_position(
                    selected_monitor,
                    match_result['center_x'],
                    match_result['center_y']
                )
                print(f"  ✓ 点击完成!")
                print()

                # 点击后可以选择继续监控或退出
                continue_choice = input("继续监控? (y/n, 默认 y): ").strip().lower()
                if continue_choice == 'n':
                    print("停止监控")
                    break

                print()
            else:
                print(f"  ✗ 未找到匹配")
                print(f"  {10} 秒后重新检测...")
                print()
                time.sleep(10)

    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
