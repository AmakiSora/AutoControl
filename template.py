import os
import cv2
import numpy as np


def load(path):
    if not os.path.exists(path):
        return None
    file_bytes = np.fromfile(path, dtype=np.uint8)
    template = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if template is None:
        return None
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    h, w = template_gray.shape
    return template_gray, w, h


def find(screenshot_gray, template_gray, w, h, threshold=0.8):
    result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    positions = list(zip(*locations[::-1]))
    if not positions:
        return None
    x, y = positions[0]
    return {
        'x': x, 'y': y,
        'center_x': x + w // 2, 'center_y': y + h // 2,
        'width': w, 'height': h,
        'confidence': float(result[y, x]),
    }
