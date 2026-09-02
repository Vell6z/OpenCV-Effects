"""
effects/slice.py
----------------
Efecto de corte en bandas horizontales desplazadas lateralmente.
"""

import numpy as np
import random


def glitch_slice(patch, intensity):
    """Corta el parche en bandas horizontales y las desplaza lateralmente."""
    h, w = patch.shape[:2]
    if h < 4 or w < 4:
        return patch
    out = patch.copy()
    n_slices = max(3, int(intensity * 0.4))
    slice_h = max(1, h // n_slices)
    max_shift = max(1, int(intensity * 0.6))

    for i in range(0, h, slice_h):
        band = out[i:i + slice_h]
        if band.shape[0] == 0:
            continue
        shift = random.randint(-max_shift, max_shift)
        out[i:i + slice_h] = np.roll(band, shift, axis=1)

    return out
