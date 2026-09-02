"""
hand_tracking.py
----------------
Lógica de detección/encuadre de manos con MediaPipe, suavizado de
coordenadas, rotación del visor y dibujado de bordes.
"""

import cv2
import numpy as np
import random

from config import MIN_BOX_SIZE, BOX_PADDING, SMOOTHING


# ----------------------------------------------------------------------------
# UTILIDADES DE SUAVIZADO
# ----------------------------------------------------------------------------
class SmoothBox:
    """Suaviza las coordenadas del cuadro para evitar temblores frame a frame."""

    def __init__(self, alpha=SMOOTHING):
        self.alpha = alpha
        self.box = None  # (x1, y1, x2, y2)

    def update(self, new_box):
        if self.box is None:
            self.box = list(new_box)
        else:
            for i in range(4):
                self.box[i] = self.alpha * self.box[i] + (1 - self.alpha) * new_box[i]
        return tuple(int(v) for v in self.box)


class SmoothRotBox:
    """Suaviza (cx, cy, w, h, angle) para evitar temblores/saltos frame a
    frame, con manejo especial del angulo para que no 'salte' al cruzar
    +-90 grados."""

    def __init__(self, alpha=SMOOTHING):
        self.alpha = alpha
        self.state = None  # [cx, cy, w, h, angle]

    def update(self, new_state):
        cx, cy, w_, h_, angle = new_state
        if self.state is None:
            self.state = [cx, cy, w_, h_, angle]
        else:
            a = self.alpha
            # angulo: interpolar por el camino mas corto
            prev_angle = self.state[4]
            diff = angle - prev_angle
            if diff > 90:
                angle -= 180
            elif diff < -90:
                angle += 180
            self.state[0] = a * self.state[0] + (1 - a) * cx
            self.state[1] = a * self.state[1] + (1 - a) * cy
            self.state[2] = a * self.state[2] + (1 - a) * w_
            self.state[3] = a * self.state[3] + (1 - a) * h_
            self.state[4] = a * prev_angle + (1 - a) * angle
        return tuple(self.state)


# ----------------------------------------------------------------------------
# LÓGICA DE ENCUADRE SEGÚN MANOS
# ----------------------------------------------------------------------------
def landmarks_to_px(hand_landmarks, w, h):
    return np.array([(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark])


def box_from_two_hands(hands_px, w, h):
    """Bounding box que envuelve todos los puntos de ambas manos."""
    all_pts = np.vstack(hands_px)
    x1, y1 = all_pts[:, 0].min(), all_pts[:, 1].min()
    x2, y2 = all_pts[:, 0].max(), all_pts[:, 1].max()
    x1 -= BOX_PADDING
    y1 -= BOX_PADDING
    x2 += BOX_PADDING
    y2 += BOX_PADDING
    return clamp_box(x1, y1, x2, y2, w, h)


def box_from_finger_frame(hands_px_list, w, h):
    """Usa pulgar (4) e índice (8) de cada mano para armar un encuadre tipo
    'visor de cámara'. Con una sola mano usa esos dos dedos; con dos manos,
    toma el punto extremo de cada mano para ampliar el marco."""
    pts = []
    for hp in hands_px_list:
        pts.append(hp[4])   # punta del pulgar
        pts.append(hp[8])   # punta del índice
    pts = np.array(pts)
    x1, y1 = pts[:, 0].min(), pts[:, 1].min()
    x2, y2 = pts[:, 0].max(), pts[:, 1].max()
    x1 -= BOX_PADDING // 2
    y1 -= BOX_PADDING // 2
    x2 += BOX_PADDING // 2
    y2 += BOX_PADDING // 2
    return clamp_box(x1, y1, x2, y2, w, h)


def rotated_rect_from_hands(hands_px_list, w, h):
    """Calcula un rectangulo ROTADO (centro, tamaño, angulo) a partir de las
    manos, para el look tipo 'visor inclinado' de la referencia:
      - Con DOS manos: el angulo es el que forma la linea entre ambas manos
        (usando la muñeca, landmark 0) respecto a la horizontal. El rectangulo
        se arma con las puntas de pulgar+indice de ambas manos, luego se
        proyecta sobre los ejes rotados.
      - Con UNA mano: el angulo es el que forma el vector pulgar->indice.
    Retorna (cx, cy, rect_w, rect_h, angle_deg).
    """
    pts_frame = []
    for hp in hands_px_list:
        pts_frame.append(hp[4])
        pts_frame.append(hp[8])
    pts_frame = np.array(pts_frame, dtype=np.float32)

    if len(hands_px_list) >= 2:
        c1, c2 = hands_px_list[0][0], hands_px_list[1][0]
        vec = c2.astype(np.float32) - c1.astype(np.float32)
    else:
        thumb, index = hands_px_list[0][4], hands_px_list[0][8]
        vec = index.astype(np.float32) - thumb.astype(np.float32)

    angle = float(np.degrees(np.arctan2(vec[1], vec[0])))
    # normalizar para que el rectangulo no quede "de cabeza" (evita saltos
    # de +-180 que harian girar el marco bruscamente)
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    cx, cy = pts_frame[:, 0].mean(), pts_frame[:, 1].mean()

    # proyectar los puntos sobre los ejes rotados para medir ancho/alto reales
    theta = np.radians(angle)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    rel = pts_frame - np.array([cx, cy], dtype=np.float32)
    local_x = rel[:, 0] * cos_t + rel[:, 1] * sin_t
    local_y = -rel[:, 0] * sin_t + rel[:, 1] * cos_t

    rect_w = float(local_x.max() - local_x.min()) + BOX_PADDING
    rect_h = float(local_y.max() - local_y.min()) + BOX_PADDING
    rect_w = max(MIN_BOX_SIZE, rect_w)
    rect_h = max(MIN_BOX_SIZE, rect_h)

    return cx, cy, rect_w, rect_h, angle


def get_rotated_patch(frame, cx, cy, rect_w, rect_h, angle_deg):
    """Extrae de 'frame' el contenido dentro del rectangulo rotado, ya
    enderezado (como si se hiciera un crop normal), listo para aplicarle
    el efecto de imagen."""
    rect_w_i, rect_h_i = max(2, int(rect_w)), max(2, int(rect_h))
    M = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
    h, w = frame.shape[:2]
    rotated_full = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REFLECT)
    x1 = int(cx - rect_w_i / 2)
    y1 = int(cy - rect_h_i / 2)
    x2, y2 = x1 + rect_w_i, y1 + rect_h_i
    x1c, y1c = max(0, x1), max(0, y1)
    x2c, y2c = min(w, x2), min(h, y2)
    if x2c <= x1c or y2c <= y1c:
        return None
    patch = rotated_full[y1c:y2c, x1c:x2c]
    # si el rectangulo ideal se salia del frame, el patch queda mas chico
    # que rect_w_i x rect_h_i; se reescala para mantener tamaño consistente
    if patch.shape[0] != rect_h_i or patch.shape[1] != rect_w_i:
        patch = cv2.resize(patch, (rect_w_i, rect_h_i))
    return patch


def paste_rotated_patch(display, patch, cx, cy, rect_w, rect_h, angle_deg):
    """Pega 'patch' (ya procesado, alineado horizontalmente) de vuelta en
    'display' rotandolo angle_deg grados alrededor de (cx, cy), con una
    mascara para que solo se pinte el area del rectangulo rotado (encima de
    lo que ya habia, como un sello). Retorna (imagen_resultado, mascara_rotada)."""
    h, w = display.shape[:2]
    rect_w_i, rect_h_i = max(2, int(rect_w)), max(2, int(rect_h))

    ph, pw = patch.shape[:2]
    if ph != rect_h_i or pw != rect_w_i:
        patch = cv2.resize(patch, (rect_w_i, rect_h_i))

    # Lienzo del tamaño del frame, con el patch ya colocado (sin rotar) en
    # su posicion centrada en (cx, cy)
    canvas = np.zeros_like(display)
    mask = np.zeros((h, w), dtype=np.uint8)
    x1 = int(cx - rect_w_i / 2)
    y1 = int(cy - rect_h_i / 2)
    x2, y2 = x1 + rect_w_i, y1 + rect_h_i
    x1c, y1c = max(0, x1), max(0, y1)
    x2c, y2c = min(w, x2), min(h, y2)
    if x2c <= x1c or y2c <= y1c:
        empty_mask = np.zeros((h, w), dtype=np.uint8)
        return display, empty_mask

    px1, py1 = x1c - x1, y1c - y1
    px2, py2 = px1 + (x2c - x1c), py1 + (y2c - y1c)
    canvas[y1c:y2c, x1c:x2c] = patch[py1:py2, px1:px2]
    mask[y1c:y2c, x1c:x2c] = 255

    # Rotar canvas y mascara alrededor de (cx, cy) por -angle_deg para
    # "devolver" la inclinacion original a la escena
    M_inv = cv2.getRotationMatrix2D((cx, cy), -angle_deg, 1.0)
    rotated_canvas = cv2.warpAffine(canvas, M_inv, (w, h), flags=cv2.INTER_LINEAR)
    rotated_mask = cv2.warpAffine(mask, M_inv, (w, h), flags=cv2.INTER_LINEAR)

    mask_3ch = cv2.merge([rotated_mask] * 3).astype(np.float32) / 255.0
    result = display.astype(np.float32) * (1 - mask_3ch) + rotated_canvas.astype(np.float32) * mask_3ch
    return result.astype(np.uint8), rotated_mask


def draw_broken_glass_border(display, rotated_mask, color=(220, 60, 230), thickness=3,
                              jitter=6, n_extra_lines=5):
    """Dibuja un borde tipo 'vidrio roto' (lineas irregulares, no un
    rectangulo perfecto) siguiendo el contorno de la mascara rotada, en un
    color magenta brillante como en la referencia visual."""
    contours, _ = cv2.findContours(rotated_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return display
    contour = max(contours, key=cv2.contourArea)

    # glow: primero una linea gruesa semi-transparente para dar brillo,
    # luego el borde nitido encima
    overlay = display.copy()
    cv2.drawContours(overlay, [contour], -1, color, thickness + 5)
    display = cv2.addWeighted(overlay, 0.35, display, 0.65, 0)

    jittered = contour.copy().astype(np.int32)
    if len(jittered) > 2:
        noise = np.random.randint(-jitter, jitter + 1, jittered.shape)
        jittered = jittered + noise
    cv2.drawContours(display, [jittered], -1, color, thickness)

    # unas "grietas" extra: lineas cortas aleatorias que salen del contorno,
    # como fracturas de vidrio
    pts = contour.reshape(-1, 2)
    if len(pts) > 5:
        for _ in range(n_extra_lines):
            idx = random.randint(0, len(pts) - 1)
            p1 = tuple(pts[idx])
            crack_len = random.randint(10, 25)
            crack_angle = random.uniform(0, 2 * np.pi)
            p2 = (int(p1[0] + crack_len * np.cos(crack_angle)),
                  int(p1[1] + crack_len * np.sin(crack_angle)))
            cv2.line(display, p1, p2, color, 1, cv2.LINE_AA)

    return display


def box_from_center_zoom(hands_px_list, w, h):
    """Centra el cuadro en el punto medio de las manos (usando la muñeca,
    landmark 0) y escala el tamaño según la distancia entre ellas."""
    centers = [hp[0] for hp in hands_px_list]
    if len(centers) == 1:
        cx, cy = centers[0]
        size = 200
    else:
        c1, c2 = centers[0], centers[1]
        cx, cy = (c1 + c2) // 2
        size = int(np.linalg.norm(c1 - c2))
        size = max(MIN_BOX_SIZE * 2, size)
    x1, y1 = cx - size // 2, cy - size // 2
    x2, y2 = cx + size // 2, cy + size // 2
    return clamp_box(x1, y1, x2, y2, w, h)


def clamp_box(x1, y1, x2, y2, w, h):
    x1 = max(0, min(int(x1), w - 2))
    y1 = max(0, min(int(y1), h - 2))
    x2 = max(x1 + MIN_BOX_SIZE, min(int(x2), w))
    y2 = max(y1 + MIN_BOX_SIZE, min(int(y2), h))
    return (x1, y1, x2, y2)


MODES = ["dos_manos_bbox", "encuadre_dedos", "zoom_centro"]
MODE_LABELS = {
    "dos_manos_bbox": "Cuadro: bounding box de ambas manos",
    "encuadre_dedos": "Cuadro: pulgar+indice (visor de camara)",
    "zoom_centro": "Cuadro: centro entre manos + zoom por distancia",
}


def compute_box(mode, hands_px_list, w, h):
    if mode == "dos_manos_bbox":
        return box_from_two_hands(hands_px_list, w, h)
    elif mode == "encuadre_dedos":
        return box_from_finger_frame(hands_px_list, w, h)
    elif mode == "zoom_centro":
        return box_from_center_zoom(hands_px_list, w, h)
    return box_from_two_hands(hands_px_list, w, h)
