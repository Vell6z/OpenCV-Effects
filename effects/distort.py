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
    """Aplica un blur gaussiano fuerte al contenido del visor.
    La intensidad controla qué tan borroso queda."""
    h, w = patch.shape[:2]
    if h < 4 or w < 4:
        return patch

    # Kernel de blur proporcional a la intensidad (siempre impar)
    k = max(3, int(intensity * 0.5)) | 1

    result = cv2.GaussianBlur(patch, (k, k), 0)

    return result
