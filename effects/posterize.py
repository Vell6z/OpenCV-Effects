"""
effects/posterize.py
--------------------
Efecto posterizado duotone/cuatricromía tipo "Visor Roto" (serigrafía).
"""

import cv2
import numpy as np

from effects.slice import glitch_slice


def posterize_duotone(patch, n_colors=4, palette=None):
    """Posteriza el parche a pocos tonos y lo mapea a una paleta dura tipo
    cuatricromia (amarillo/cian/magenta/negro por defecto), como el look
    de serigrafia / print de la referencia."""
    h, w = patch.shape[:2]
    if h < 2 or w < 2:
        return patch

    if palette is None:
        # BGR: negro, magenta, cian, amarillo (de mas oscuro a mas claro)
        palette = [
            (20, 20, 20),      # negro casi puro
            (200, 30, 220),    # magenta
            (220, 200, 30),    # cian (en BGR: azul y verde altos)
            (30, 230, 240),    # amarillo (en BGR: verde y rojo altos)
        ]

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    # ecualizar para aprovechar todo el rango de tonos disponible
    gray = cv2.equalizeHist(gray)

    n_levels = len(palette)
    # bins de brillo -> indice de paleta
    bins = np.linspace(0, 256, n_levels + 1)
    level_idx = np.digitize(gray, bins[1:-1], right=True)

    out = np.zeros_like(patch)
    for i, color in enumerate(palette):
        mask = level_idx == i
        out[mask] = color

    return out


def add_halftone_texture(patch, dot_spacing=6, strength=0.25):
    """Textura sutil tipo trama de puntos (halftone) para reforzar el look
    de impresion serigrafica del posterizado."""
    h, w = patch.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    pattern = ((xx // dot_spacing + yy // dot_spacing) % 2) * strength
    pattern = (pattern * 255).astype(np.uint8)
    pattern_bgr = cv2.merge([pattern, pattern, pattern])
    return cv2.subtract(patch, pattern_bgr)


def glitch_posterize(patch, intensity):
    """Estilo 'Visor Roto': posterizado duotone/cuatricromia con un leve
    corte en bandas para que no se vea completamente estatico, mas
    fiel al efecto de la referencia (colores duros + ligero temblor)."""
    result = posterize_duotone(patch)
    # un toque de slice muy sutil, escalado por intensidad, para que la
    # imagen posterizada respire/tiemble un poco en vez de verse congelada
    if intensity > 0:
        result = glitch_slice(result, max(5, intensity * 0.25))
    return result
