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


def render_ascii_bold(patch):
    """Arte ASCII con caracteres gruesos y grandes, más impactante visualmente."""
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
        y = int(row * ASCII_BOLD_CELL_SIZE + ASCII_BOLD_CELL_SIZE * 0.8)
        for col in range(cols):
            x = int(col * ASCII_BOLD_CELL_SIZE)
            brightness = small[row, col]
            idx = min(n_levels - 1, int(brightness / 256.0 * n_levels))
            ch = ASCII_BOLD_CHARSET[idx]
            if ch == " ":
                continue
            cv2.putText(canvas, ch, (x, y), ASCII_BOLD_FONT, ASCII_BOLD_FONT_SCALE,
                        (255, 255, 255), ASCII_BOLD_FONT_THICKNESS, cv2.LINE_AA)

    return canvas
