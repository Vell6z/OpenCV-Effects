"""
effects/voxel.py
----------------
Efecto "voxel matrix": la imagen se descompone en una grilla de cubos 3D
en tonos azules, como una escultura digital pixelada.
"""

import cv2
import numpy as np


VOXEL_CELL = 12       # tamaño de cada cubo en pixeles
VOXEL_DEPTH = 4       # profundidad visual del cubo (perspectiva isometrica)


def glitch_voxel(patch, intensity):
    """Renderiza la imagen como una matriz de cubos 3D en tonos azules.
    El brillo de cada celda controla el 'alto' visual del cubo y su tono."""
    h, w = patch.shape[:2]
    cell = max(4, VOXEL_CELL)
    if h < cell or w < cell:
        return patch

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

    cols = w // cell
    rows = h // cell

    # Downsample a una celda = un valor de brillo promedio
    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)

    # Fondo oscuro azul
    canvas = np.full((h, w, 3), (15, 12, 8), dtype=np.uint8)

    depth = max(2, int(VOXEL_DEPTH * (0.5 + intensity * 0.01)))

    for row in range(rows):
        for col in range(cols):
            brightness = int(small[row, col])

            # Umbral: zonas muy oscuras no dibujan cubo (fondo limpio)
            if brightness < 25:
                continue

            # Coordenadas del cubo
            x = col * cell
            y = row * cell

            # Colores del cubo en escala de azul, basados en el brillo
            # Cara frontal: azul principal
            b_val = min(255, 80 + int(brightness * 0.7))
            g_val = min(255, 30 + int(brightness * 0.3))
            r_val = min(180, 10 + int(brightness * 0.15))
            face_color = (b_val, g_val, r_val)

            # Cara superior: más clara (luz desde arriba)
            top_color = (min(255, b_val + 40), min(255, g_val + 25), min(255, r_val + 15))

            # Cara lateral derecha: más oscura (sombra)
            side_color = (max(0, b_val - 35), max(0, g_val - 20), max(0, r_val - 10))

            # --- Dibujar cubo isométrico ---

            # Cara frontal (rectángulo principal)
            cv2.rectangle(canvas, (x, y), (x + cell - 1, y + cell - 1), face_color, -1)

            # Cara superior (paralelogramo arriba)
            top_pts = np.array([
                [x, y],
                [x + depth, y - depth],
                [x + cell - 1 + depth, y - depth],
                [x + cell - 1, y],
            ], dtype=np.int32)
            # Clamp to canvas bounds
            if y - depth >= 0:
                cv2.fillPoly(canvas, [top_pts], top_color)

            # Cara lateral derecha (paralelogramo a la derecha)
            right_pts = np.array([
                [x + cell - 1, y],
                [x + cell - 1 + depth, y - depth],
                [x + cell - 1 + depth, y + cell - 1 - depth],
                [x + cell - 1, y + cell - 1],
            ], dtype=np.int32)
            if x + cell - 1 + depth < w:
                cv2.fillPoly(canvas, [right_pts], side_color)

            # Borde sutil del cubo para separar bloques
            cv2.rectangle(canvas, (x, y), (x + cell - 1, y + cell - 1),
                          (max(0, b_val - 50), max(0, g_val - 30), max(0, r_val - 15)), 1)

    return canvas
