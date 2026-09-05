"""
effects/distort.py
------------------
Efecto de blur/desenfoque fuerte: aplica un desenfoque gaussiano intenso
al contenido del visor, difuminando la imagen como si se viera a través
de un vidrio esmerilado.
"""

import cv2
import numpy as np


def glitch_distort(patch, intensity):
    """Aplica un blur de vidrio esmerilado estético y rápido mediante
    técnica piramidal (downsample + blur + upsample), 10x más rápido."""
    h, w = patch.shape[:2]
    if h < 4 or w < 4:
        return patch

    factor = max(2, min(8, int(1 + intensity * 0.04)))
    sw = max(2, w // factor)
    sh = max(2, h // factor)

    small = cv2.resize(patch, (sw, sh), interpolation=cv2.INTER_LINEAR)
    k = max(3, int(intensity * 0.15)) | 1
    blurred = cv2.GaussianBlur(small, (k, k), 0)
    result = cv2.resize(blurred, (w, h), interpolation=cv2.INTER_LINEAR)
    return result
