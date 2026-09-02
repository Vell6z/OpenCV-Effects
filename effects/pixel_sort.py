"""
effects/pixel_sort.py
---------------------
Efecto de ordenamiento de píxeles por brillo (pixel sort).
"""

import cv2
import numpy as np
import random


def glitch_pixel_sort(patch, intensity):
    """Ordena por brillo *segmentos* aleatorios dentro de filas seleccionadas
    (no la fila completa) para lograr el look 'derretido' clasico sin que
    los pixeles de un mismo tono (ej. verdes de la piel) se agrupen en una
    franja solida y fija."""
    h, w = patch.shape[:2]
    if h < 2 or w < 4:
        return patch
    out = patch.copy()
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    n_rows = max(1, int(intensity * 0.5))
    rows = random.sample(range(h), min(n_rows, h))

    for row in rows:
        # segmento aleatorio dentro de la fila, no la fila entera
        seg_len = random.randint(w // 6, max(w // 3, w // 6 + 1))
        start = random.randint(0, max(0, w - seg_len))
        end = start + seg_len
        segment_gray = gray[row, start:end]
        idx = np.argsort(segment_gray)
        out[row, start:end] = out[row, start:end][idx]

    return out
