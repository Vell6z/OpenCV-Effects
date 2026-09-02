"""
config.py
---------
Constantes y configuración general compartida por todos los módulos
del proyecto Visor Roto.
"""

import cv2

# ----------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ----------------------------------------------------------------------------
CAM_INDEX = 3
FRAME_W, FRAME_H = 1280, 720
MIN_BOX_SIZE = 40           # tamaño mínimo del cuadro en píxeles
BOX_PADDING = 25            # margen extra alrededor del bounding box de manos
SMOOTHING = 0.35            # 0=sin suavizado, 1=totalmente suavizado (evita jitter)
OUTPUT_DIR = "/mnt/user-data/outputs"

DEFAULT_MODE_INDEX = 1      # 0=dos_manos_bbox, 1=encuadre_dedos, 2=zoom_centro
DEFAULT_INTENSITY = 85      # intensidad base del glitch (antes 40) -> mas agresivo
DEFAULT_GLITCH_INDEX = 0    # 0=posterize (estilo "Visor Roto", ver GLITCH_STYLES)
SHOW_HAND_SKELETON = False  # True = dibuja puntos/lineas de la mano (debug), False = limpio
ALLOW_ROTATION = True       # True = el cuadro se inclina segun el angulo entre manos/dedos

# "posterize" = look duotone/cuatricromia tipo "Visor Roto" (referencia visual).
# "thermal" = camara termica simulada (Selfie Segmentation + paleta ironbow).
# "ascii" = arte ASCII en tiempo real (blanco sobre negro, caracteres grandes).
# "combo" = glitch caotico full RGB (version anterior del efecto).
GLITCH_STYLES = ["posterize", "thermal", "ascii", "combo", "rgb_shift", "slice", "pixel_sort", "noise_block"]

THERMAL_SEG_THRESHOLD = 0.5   # umbral de la mascara de segmentacion (persona vs fondo)
THERMAL_BLUR_MASK = 15        # suavizado de la mascara para bordes menos duros/mas organicos

# --- Config del estilo ASCII ---
ASCII_CELL_SIZE = 10           # tamaño de celda en pixeles (mas chico = mas fino/detallado)
ASCII_CHARSET = " .:-=+*#%@"   # de mas oscuro (espacio) a mas claro (@), 10 niveles
ASCII_FONT = cv2.FONT_HERSHEY_PLAIN
ASCII_FONT_SCALE = 0.7
ASCII_FONT_THICKNESS = 1
