"""
effects/ascii_art.py
--------------------
Efecto de arte ASCII en tiempo real (caracteres blancos sobre fondo negro).
"""

import cv2
import numpy as np

from config import ASCII_CELL_SIZE, ASCII_CHARSET, ASCII_FONT, ASCII_FONT_SCALE, ASCII_FONT_THICKNESS


# Pre-renderizar glifos para evitar miles de llamadas a cv2.putText por frame
GLYPH_TILES = []
for _ch in ASCII_CHARSET:
    _tile = np.zeros((ASCII_CELL_SIZE, ASCII_CELL_SIZE, 3), dtype=np.uint8)
    if _ch != " ":
        _y = int(ASCII_CELL_SIZE * 0.8)
        cv2.putText(_tile, _ch, (0, _y), ASCII_FONT, ASCII_FONT_SCALE,
                    (255, 255, 255), ASCII_FONT_THICKNESS, cv2.LINE_AA)
    GLYPH_TILES.append(_tile)


def render_ascii_art(patch):
    """Convierte 'patch' en arte ASCII usando blitting ultrarrápido de glifos pre-renderizados."""
    h, w = patch.shape[:2]
    if h < ASCII_CELL_SIZE or w < ASCII_CELL_SIZE:
        return patch

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

    cols = max(1, w // ASCII_CELL_SIZE)
    rows = max(1, h // ASCII_CELL_SIZE)

    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((h, w, 3), dtype=np.uint8)  # fondo negro

    n_levels = len(ASCII_CHARSET)
    for row in range(rows):
        y = row * ASCII_CELL_SIZE
        for col in range(cols):
            x = col * ASCII_CELL_SIZE
            brightness = small[row, col]
            idx = min(n_levels - 1, int(brightness / 256.0 * n_levels))
            if idx > 0:
                canvas[y:y+ASCII_CELL_SIZE, x:x+ASCII_CELL_SIZE] = GLYPH_TILES[idx]

    return canvas
