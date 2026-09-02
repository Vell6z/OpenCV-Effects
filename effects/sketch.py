"""
effects/sketch.py
-----------------
Efecto de sketch/grabado detallado: líneas finas blancas sobre fondo negro
con mucho detalle en texturas (pelo, piel, ropa), como un grabado a pluma.
"""

import cv2
import numpy as np


def glitch_sketch(patch, intensity):
    """Genera un efecto de sketch detallado combinando detección de bordes
    con la técnica de pencil sketch (dodge blend), para capturar tanto
    contornos fuertes como texturas finas (pelo, tela, piel)."""
    h, w = patch.shape[:2]
    if h < 4 or w < 4:
        return patch

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

    # --- Capa 1: Pencil sketch (dodge blend) para texturas finas ---
    # Invertir -> blur -> dividir (simula luz difusa, resalta texturas)
    inv = 255 - gray
    blur_size = max(3, int(21 - intensity * 0.1)) | 1  # siempre impar
    blurred = cv2.GaussianBlur(inv, (blur_size, blur_size), 0)
    # Dodge blend: divide gray / (255 - blurred), escalado a 255
    blurred_inv = 255 - blurred
    blurred_inv[blurred_inv == 0] = 1  # evitar division por cero
    sketch = np.clip((gray.astype(np.float32) * 256) / blurred_inv.astype(np.float32), 0, 255).astype(np.uint8)

    # Invertir para que sea blanco-sobre-negro (lineas blancas, fondo negro)
    sketch = 255 - sketch

    # --- Capa 2: Laplacian para bordes mas definidos ---
    lap = cv2.Laplacian(gray, cv2.CV_16S, ksize=3)
    lap = np.clip(np.abs(lap), 0, 255).astype(np.uint8)

    # Combinar ambas capas: el sketch da textura, el laplacian da contornos
    alpha = min(0.7, 0.3 + intensity * 0.004)
    combined = cv2.addWeighted(sketch, alpha, lap, 1.0 - alpha, 0)

    # Realzar contraste para que las lineas sean mas blancas y el fondo mas negro
    combined = cv2.normalize(combined, None, 0, 255, cv2.NORM_MINMAX)

    # Umbral suave para limpiar ruido de fondo sin perder detalle
    _, mask = cv2.threshold(combined, max(15, 40 - int(intensity * 0.2)), 255, cv2.THRESH_BINARY)
    combined = cv2.bitwise_and(combined, mask)

    canvas = cv2.merge([combined, combined, combined])
    return canvas
