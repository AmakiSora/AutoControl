import mss
import numpy as np
import cv2


def get_monitors():
    with mss.mss() as sct:
        return sct.monitors


def capture_monitor(monitor_index):
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        return img_bgr, img_gray, monitor


def to_global(monitor, rel_x, rel_y):
    return monitor['left'] + rel_x, monitor['top'] + rel_y
