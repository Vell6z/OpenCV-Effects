"""
effects/rgb_shift.py
--------------------
Efecto de desplazamiento independiente de canales de color (RGB shift).
"""

import cv2
import numpy as np
import random


def glitch_rgb_shift(patch, intensity):
    """Desplaza los canales de color de forma independiente."""
    h, w = patch.shape[:2]
    if h < 2 or w < 2:
        return patch
    b, g, r = cv2.split(patch)
    max_shift = max(1, int(intensity * 0.15))

    def shift_channel(ch):
        dx = random.randint(-max_shift, max_shift)
        dy = random.randint(-max_shift, max_shift)
        m = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(ch, m, (w, h), borderMode=cv2.BORDER_REFLECT)

    b2 = shift_channel(b)
    r2 = shift_channel(r)
    return cv2.merge([b2, g, r2])
