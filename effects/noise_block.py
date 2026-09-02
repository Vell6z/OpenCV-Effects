"""
effects/noise_block.py
----------------------
Efecto de bloques de ruido/estática superpuestos.
"""

import cv2
import numpy as np
import random


def glitch_noise_block(patch, intensity):
    """Inserta bloques de ruido/estática en posiciones aleatorias."""
    h, w = patch.shape[:2]
    if h < 4 or w < 4:
        return patch
    out = patch.copy()
    n_blocks = max(1, int(intensity * 0.3))

    for _ in range(n_blocks):
        bw = random.randint(w // 12 + 1, max(w // 6, w // 12 + 2))
        bh = random.randint(h // 12 + 1, max(h // 6, h // 12 + 2))
        x = random.randint(0, max(0, w - bw))
        y = random.randint(0, max(0, h - bh))
        noise = np.random.randint(0, 255, (bh, bw, 3), dtype=np.uint8)
        alpha = 0.85
        out[y:y + bh, x:x + bw] = cv2.addWeighted(
            out[y:y + bh, x:x + bw], 1 - alpha, noise, alpha, 0
        )

    return out
