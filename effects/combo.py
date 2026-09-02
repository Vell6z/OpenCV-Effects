"""
effects/combo.py
----------------
Efecto glitch caótico que apila varias técnicas en un solo frame.
"""

import numpy as np
import random

from effects.rgb_shift import glitch_rgb_shift
from effects.slice import glitch_slice
from effects.pixel_sort import glitch_pixel_sort
from effects.noise_block import glitch_noise_block
from effects.scanlines import glitch_scanlines


def glitch_combo(patch, intensity):
    """Apila varias tecnicas de glitch en un solo frame para un resultado
    mucho mas caotico/roto: slice + pixel_sort parcial + rgb_shift fuerte +
    bloques de ruido + scanlines. Pensado como el estilo 'por defecto' mas
    agresivo del script."""
    h, w = patch.shape[:2]
    if h < 4 or w < 4:
        return patch

    result = patch.copy()

    # 1) corte en bandas (siempre)
    result = glitch_slice(result, intensity * 1.2)

    # 2) pixel sort en una fraccion de los frames (no siempre, para que
    #    parpadee entre estados distintos, mas organico)
    if random.random() < 0.6:
        result = glitch_pixel_sort(result, intensity * 0.7)

    # 3) desplazamiento de canales fuerte
    result = glitch_rgb_shift(result, intensity * 1.3)

    # 4) bloques de ruido superpuestos
    if random.random() < 0.75:
        result = glitch_noise_block(result, intensity * 0.9)

    # 5) scanlines para textura tipo señal rota
    if random.random() < 0.5:
        result = glitch_scanlines(result, intensity)

    # 6) invertir colores en franjas aleatorias, ocasional, para picos de glitch
    if random.random() < 0.15:
        h2, w2 = result.shape[:2]
        y0 = random.randint(0, max(0, h2 - 1))
        band_h = max(1, int(h2 * random.uniform(0.05, 0.2)))
        y1 = min(h2, y0 + band_h)
        result[y0:y1] = 255 - result[y0:y1]

    return result
