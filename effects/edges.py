"""
effects/edges.py
----------------
Efecto de detección de bordes tipo "contorno neon": solo se ven los
bordes/siluetas en blanco brillante sobre fondo negro, como un dibujo
de líneas en tiempo real.
"""

import cv2
import numpy as np


def glitch_edges(patch, intensity):
    """Detecta bordes con Canny y los muestra como líneas blancas gruesas
    sobre fondo negro. La intensidad controla la sensibilidad de detección
    y el grosor de las líneas."""
    h, w = patch.shape[:2]
    if h < 4 or w < 4:
        return patch

    # Convertir a escala de grises y suavizar para reducir ruido
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 1.2)

    # Umbrales de Canny: intensidad baja = más bordes visibles,
    # intensidad alta = solo bordes fuertes
    low_thresh = max(10, 120 - int(intensity * 0.8))
    high_thresh = max(30, 200 - int(intensity * 0.6))
    edges = cv2.Canny(blur, low_thresh, high_thresh)

    # Engrosar los bordes con dilatación para que se vean más sólidos
    kernel_size = max(1, int(intensity / 40)) * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    edges_thick = cv2.dilate(edges, kernel, iterations=1)

    # Glow: aplicar un blur suave sobre los bordes y sumarlos para
    # dar un brillo tipo neon alrededor de cada línea
    glow = cv2.GaussianBlur(edges_thick, (0, 0), 3)
    combined = cv2.add(edges_thick, glow)

    # Convertir a BGR (blanco sobre negro)
    canvas = cv2.merge([combined, combined, combined])

    return canvas
