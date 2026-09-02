"""
effects/scanlines.py
--------------------
Efecto de scanlines tipo VHS/CRT.
"""

import numpy as np
import random


def glitch_scanlines(patch, intensity):
    """Oscurece/satura lineas horizontales alternas, look VHS/CRT roto.
    Evita factores >1 tan altos que saturen un canal completo y generen
    una banda de color solido (ej. verde) en vez de textura de ruido."""
    h, w = patch.shape[:2]
    if h < 2:
        return patch
    out = patch.copy().astype(np.int16)
    step = max(2, 6 - int(intensity / 40))
    for y in range(0, h, step):
        # rango mas conservador: solo oscurece o realza levemente,
        # nunca lo suficiente para que un canal se sature parejo
        factor = random.uniform(0.35, 1.15)
        out[y] = np.clip(out[y] * factor, 0, 255)
    return out.astype(np.uint8)
