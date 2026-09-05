"""
effects/ascii_bold.py
---------------------
Efecto de arte ASCII en tiempo real con caracteres GRUESOS (bold).
"""

import cv2
import numpy as np


ASCII_BOLD_CELL_SIZE = 16
ASCII_BOLD_CHARSET = " .:-=+*#%@"
ASCII_BOLD_FONT = cv2.FONT_HERSHEY_SIMPLEX
ASCII_BOLD_FONT_SCALE = 0.6
ASCII_BOLD_FONT_THICKNESS = 2


# Pre-renderizar glifos bold para máximo rendimiento
BOLD_GLYPH_TILES = []
for _ch in ASCII_BOLD_CHARSET:
    _tile = np.zeros((ASCII_BOLD_CELL_SIZE, ASCII_BOLD_CELL_SIZE, 3), dtype=np.uint8)
    if _ch != " ":
        _y = int(ASCII_BOLD_CELL_SIZE * 0.8)
        cv2.putText(_tile, _ch, (0, _y), ASCII_BOLD_FONT, ASCII_BOLD_FONT_SCALE,
                    (255, 255, 255), ASCII_BOLD_FONT_THICKNESS, cv2.LINE_AA)
    BOLD_GLYPH_TILES.append(_tile)


def render_ascii_bold(patch):
    """Arte ASCII con caracteres gruesos optimizado con blitting de bloques."""
    h, w = patch.shape[:2]
    if h < ASCII_BOLD_CELL_SIZE or w < ASCII_BOLD_CELL_SIZE:
        return patch

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

    cols = max(1, w // ASCII_BOLD_CELL_SIZE)
    rows = max(1, h // ASCII_BOLD_CELL_SIZE)

    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    n_levels = len(ASCII_BOLD_CHARSET)
    for row in range(rows):
        y = row * ASCII_BOLD_CELL_SIZE
        for col in range(cols):
            x = col * ASCII_BOLD_CELL_SIZE
            brightness = small[row, col]
            idx = min(n_levels - 1, int(brightness / 256.0 * n_levels))
            if idx > 0:
                canvas[y:y+ASCII_BOLD_CELL_SIZE, x:x+ASCII_BOLD_CELL_SIZE] = BOLD_GLYPH_TILES[idx]

    return canvas
