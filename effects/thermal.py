"""
effects/thermal.py
------------------
Efecto de cámara térmica simulada usando MediaPipe Selfie Segmentation.
"""

import cv2
import numpy as np

from config import THERMAL_BLUR_MASK


def thermal_colorize(intensity_map):
    """Convierte un mapa de 'intensidad de calor' (0-255, uint8, 1 canal) en
    una imagen BGR con paleta tipo 'ironbow' de camara termica:
    negro/azul (frio) -> rojo/naranja (calor corporal) -> amarillo/blanco
    (puntos mas calientes: cabeza, manos, pecho)."""
    # cv2.COLORMAP_JET va de azul(frio)->verde->amarillo->rojo(caliente),
    # muy parecido al ejemplo (fondo azul oscuro, cuerpo rojo/naranja,
    # bordes verdes/amarillos). Se aplica directo sobre el mapa de intensidad.
    colored = cv2.applyColorMap(intensity_map, cv2.COLORMAP_JET)
    return colored


def build_thermal_frame(frame_bgr, seg_mask_float):
    """Genera la version 'camara termica' del frame COMPLETO:
      - Dentro de la persona (mask alta): intensidad basada en brillo real
        de la piel/ropa (simula variacion de 'calor'), mapeada a colores
        calidos (rojo/naranja/amarillo).
      - Fuera de la persona (mask baja): fondo casi negro/azul muy oscuro,
        como en una camara termica real donde el ambiente frio se ve oscuro.
    seg_mask_float: array HxW, valores 0..1 (probabilidad de ser persona).
    """
    h, w = frame_bgr.shape[:2]
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # suavizar mascara para bordes organicos, no recortados a la perfeccion
    mask_smooth = cv2.GaussianBlur(seg_mask_float, (0, 0), THERMAL_BLUR_MASK / 3.0)
    mask_smooth = np.clip(mask_smooth, 0, 1)

    # Base de "intensidad de calor": el cuerpo se mapea a un rango alto
    # (150-255, para caer en rojo/naranja/amarillo de JET), el fondo a un
    # rango bajo (0-40, para caer en azul oscuro/negro de JET).
    person_heat = 150 + (gray / 255.0) * 90     # 150..240 aprox
    bg_heat = 10 + (gray / 255.0) * 25          # 10..35 aprox

    heat = person_heat * mask_smooth + bg_heat * (1 - mask_smooth)
    heat = np.clip(heat, 0, 255).astype(np.uint8)

    thermal = thermal_colorize(heat)

    # leve ruido tipo sensor termico real, para que no se vea plano
    noise = np.random.normal(0, 4, thermal.shape).astype(np.int16)
    thermal = np.clip(thermal.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return thermal
