"""
effects/ascii_art.py
--------------------
Efecto de arte ASCII en tiempo real (caracteres blancos sobre fondo negro).
"""

import cv2
import numpy as np

from config import ASCII_CELL_SIZE, ASCII_CHARSET, ASCII_FONT, ASCII_FONT_SCALE, ASCII_FONT_THICKNESS


def render_ascii_art(patch):
    """Convierte 'patch' en arte ASCII: downsamplea a una grilla de celdas
    de ASCII_CELL_SIZE pixeles, mapea el brillo promedio de cada celda a un
    caracter de ASCII_CHARSET (de oscuro a claro), y dibuja esos caracteres
    en blanco sobre fondo negro -- estilo 'terminal art' de la referencia."""
    h, w = patch.shape[:2]
    if h < ASCII_CELL_SIZE or w < ASCII_CELL_SIZE:
        return patch

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

    cols = max(1, w // ASCII_CELL_SIZE)
    rows = max(1, h // ASCII_CELL_SIZE)

    # downsample a una celda = un pixel promedio de brillo, luego se vuelve
    # a mapear cada celda a un caracter
    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)

    canvas = np.zeros((h, w, 3), dtype=np.uint8)  # fondo negro

    n_levels = len(ASCII_CHARSET)
    for row in range(rows):
        y = int(row * ASCII_CELL_SIZE + ASCII_CELL_SIZE * 0.8)
        for col in range(cols):
            x = int(col * ASCII_CELL_SIZE)
            brightness = small[row, col]
            idx = min(n_levels - 1, int(brightness / 256.0 * n_levels))
            ch = ASCII_CHARSET[idx]
            if ch == " ":
                continue
            cv2.putText(canvas, ch, (x, y), ASCII_FONT, ASCII_FONT_SCALE,
                        (255, 255, 255), ASCII_FONT_THICKNESS, cv2.LINE_AA)

    return canvas
