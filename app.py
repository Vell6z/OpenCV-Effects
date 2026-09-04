"""
app.py
------
Servidor web Flask + SocketIO que expone los efectos visuales de OpenCV
con detección de manos MediaPipe — el efecto se aplica SOLO dentro del
recuadro formado por las manos, igual que la versión de escritorio.

Uso:
    python app.py

Luego abrir http://localhost:5000 en el navegador (o la IP local para
otros dispositivos en la misma red).
"""

import base64
import cv2
import numpy as np
import mediapipe as mp
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# ---- Importar efectos ----
from effects.posterize import glitch_posterize
from effects.thermal import build_thermal_frame
from effects.ascii_art import render_ascii_art
from effects.ascii_bold import render_ascii_bold
from effects.edges import glitch_edges
from effects.sketch import glitch_sketch
from effects.voxel import glitch_voxel
from effects.distort import glitch_distort
from effects.combo import glitch_combo
from effects.rgb_shift import glitch_rgb_shift
from effects.slice import glitch_slice
from effects.pixel_sort import glitch_pixel_sort
from effects.noise_block import glitch_noise_block

# ---- Importar lógica de hand tracking ----
from hand_tracking import (
    SmoothBox, SmoothRotBox, landmarks_to_px,
    rotated_rect_from_hands, get_rotated_patch, paste_rotated_patch,
    draw_broken_glass_border, compute_box,
    MODES, MODE_LABELS,
)

from config import (
    DEFAULT_MODE_INDEX, DEFAULT_INTENSITY,
    SHOW_HAND_SKELETON, ALLOW_ROTATION,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "visor-roto-secret"
app.config["TEMPLATES_AUTO_RELOAD"] = True
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10 * 1024 * 1024)

# ---- MediaPipe Hands (se inicializa una vez) ----
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles
mp_selfie = mp.solutions.selfie_segmentation

hands_detector = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6,
)

selfie_segmentor = mp_selfie.SelfieSegmentation(model_selection=1)

# ---- Registro de efectos ----
EFFECTS = {
    "posterize": {
        "func": glitch_posterize,
        "name": "Posterize",
        "desc": "Duotone / serigrafía con 4 colores",
        "emoji": "🎨",
        "needs_segmentation": False,
    },
    "thermal": {
        "func": lambda patch, intensity: patch,  # se maneja aparte
        "name": "Thermal",
        "desc": "Cámara térmica simulada",
        "emoji": "🌡️",
        "needs_segmentation": True,
    },
    "ascii": {
        "func": lambda patch, intensity: render_ascii_art(patch),
        "name": "ASCII Art",
        "desc": "Caracteres ASCII finos",
        "emoji": "🔤",
        "needs_segmentation": False,
    },
    "ascii_bold": {
        "func": lambda patch, intensity: render_ascii_bold(patch),
        "name": "ASCII Bold",
        "desc": "ASCII grueso e impactante",
        "emoji": "🅰️",
        "needs_segmentation": False,
    },
    "edges": {
        "func": glitch_edges,
        "name": "Edges",
        "desc": "Contornos neón tipo Canny",
        "emoji": "✨",
        "needs_segmentation": False,
    },
    "sketch": {
        "func": glitch_sketch,
        "name": "Sketch",
        "desc": "Grabado a pluma con texturas",
        "emoji": "✏️",
        "needs_segmentation": False,
    },
    "voxel": {
        "func": glitch_voxel,
        "name": "Voxel",
        "desc": "Cubos 3D isométricos azules",
        "emoji": "🧊",
        "needs_segmentation": False,
    },
    "distort": {
        "func": glitch_distort,
        "name": "Distort",
        "desc": "Blur / vidrio esmerilado",
        "emoji": "🌀",
        "needs_segmentation": False,
    },
    "combo": {
        "func": glitch_combo,
        "name": "Combo",
        "desc": "Glitch caótico combinado",
        "emoji": "💥",
        "needs_segmentation": False,
    },
    "rgb_shift": {
        "func": glitch_rgb_shift,
        "name": "RGB Shift",
        "desc": "Desplazamiento de canales",
        "emoji": "🌈",
        "needs_segmentation": False,
    },
    "slice": {
        "func": glitch_slice,
        "name": "Slice",
        "desc": "Bandas horizontales desplazadas",
        "emoji": "📊",
        "needs_segmentation": False,
    },
    "pixel_sort": {
        "func": glitch_pixel_sort,
        "name": "Pixel Sort",
        "desc": "Ordenamiento por brillo",
        "emoji": "📶",
        "needs_segmentation": False,
    },
    "noise_block": {
        "func": glitch_noise_block,
        "name": "Noise Block",
        "desc": "Bloques de ruido estático",
        "emoji": "📺",
        "needs_segmentation": False,
    },
}

# ---- Estado global ----
current_effect = "posterize"
current_intensity = DEFAULT_INTENSITY
mode_idx = DEFAULT_MODE_INDEX
show_skeleton = SHOW_HAND_SKELETON
allow_rotation = ALLOW_ROTATION

# Smoothers (persistentes entre frames para suavizar el cuadro)
smoother = SmoothBox()
rot_smoother = SmoothRotBox()
last_box = None
last_rot_state = None


def decode_frame(data_url):
    """Decodifica un frame JPEG base64 (data URL) a un array BGR de OpenCV."""
    header, encoded = data_url.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame


def encode_frame(frame, quality=75):
    """Codifica un frame BGR de OpenCV a JPEG base64 data URL."""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode(".jpg", frame, encode_params)
    b64 = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def process_frame_with_hands(frame, effect_key, intensity):
    """Procesa un frame: detecta manos, calcula el recuadro, aplica el
    efecto SOLO dentro del recuadro (igual que run_effect.py)."""
    global last_box, last_rot_state, smoother, rot_smoother

    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands_detector.process(rgb)

    display = frame.copy()
    mode = MODES[mode_idx]
    use_rotation = allow_rotation and mode == "encuadre_dedos"

    # Fuente del frame (normal o thermal)
    effect_info = EFFECTS.get(effect_key, EFFECTS["posterize"])
    source_frame = frame
    if effect_info["needs_segmentation"] and effect_key == "thermal":
        seg_result = selfie_segmentor.process(rgb)
        seg_mask = seg_result.segmentation_mask
        source_frame = build_thermal_frame(frame, seg_mask)

    process_func = effect_info["func"]

    box = last_box
    rot_state = last_rot_state

    if results.multi_hand_landmarks:
        hands_px = [landmarks_to_px(hl, w, h) for hl in results.multi_hand_landmarks]

        if show_skeleton:
            for hl in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(
                    display, hl, mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style(),
                )

        if use_rotation:
            raw_rot = rotated_rect_from_hands(hands_px, w, h)
            rot_state = rot_smoother.update(raw_rot)
            last_rot_state = rot_state
        else:
            raw_box = compute_box(mode, hands_px, w, h)
            box = smoother.update(raw_box)
            last_box = box

    # ---- Aplicar efecto en el recuadro ----
    if use_rotation and rot_state is not None:
        cx, cy, rw, rh, angle = rot_state
        patch = get_rotated_patch(source_frame, cx, cy, rw, rh, angle)
        if patch is not None:
            try:
                processed = process_func(patch, intensity)
                if processed is None or processed.shape != patch.shape:
                    processed = patch
            except Exception:
                processed = patch

            display, rotated_mask = paste_rotated_patch(
                display, processed, cx, cy, rw, rh, angle
            )
            display = draw_broken_glass_border(display, rotated_mask)

    elif box is not None:
        x1, y1, x2, y2 = box
        x1c, y1c = max(0, x1), max(0, y1)
        x2c, y2c = min(w, x2), min(h, y2)

        if x2c > x1c and y2c > y1c:
            patch = source_frame[y1c:y2c, x1c:x2c].copy()
            try:
                glitched = process_func(patch, intensity)
                if glitched is None:
                    glitched = patch
            except Exception:
                glitched = patch

            if glitched.shape[:2] == (y2c - y1c, x2c - x1c):
                display[y1c:y2c, x1c:x2c] = glitched

            # Dibujar borde del cuadro
            cv2.rectangle(display, (x1c, y1c), (x2c, y2c), (0, 255, 255), 2)
            corner_len = 18
            corners = [(x1c, y1c, 1, 1), (x2c, y1c, -1, 1),
                       (x1c, y2c, 1, -1), (x2c, y2c, -1, -1)]
            for cx, cy, dx, dy in corners:
                cv2.line(display, (cx, cy), (cx + dx * corner_len, cy), (0, 255, 255), 3)
                cv2.line(display, (cx, cy), (cx, cy + dy * corner_len), (0, 255, 255), 3)

    # HUD
    hud_lines = [
        MODE_LABELS[MODES[mode_idx]] + (" [rotando]" if use_rotation else ""),
        f"Efecto: {effect_key}  (intensidad: {intensity})",
    ]
    y_off = 25
    for line in hud_lines:
        if not line:
            continue
        cv2.putText(display, line, (15, y_off), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(display, line, (15, y_off), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 255), 1, cv2.LINE_AA)
        y_off += 24

    return display


# ---- Rutas ----
@app.route("/")
def index():
    return render_template("index.html", effects=EFFECTS)


def get_state_payload():
    """Genera el payload con el estado completo para enviar al cliente."""
    return {
        "effect": current_effect,
        "intensity": current_intensity,
        "mode_idx": mode_idx,
        "mode_label": MODE_LABELS[MODES[mode_idx]],
        "modes": [{"key": m, "label": MODE_LABELS[m]} for m in MODES],
        "show_skeleton": show_skeleton,
        "allow_rotation": allow_rotation,
        "effects_list": {
            k: {"name": v["name"], "desc": v["desc"], "emoji": v["emoji"]}
            for k, v in EFFECTS.items()
        },
    }


# ---- WebSocket events ----
@socketio.on("connect")
def handle_connect():
    emit("state_update", get_state_payload())


@socketio.on("video_frame")
def handle_video_frame(data):
    try:
        frame = decode_frame(data["frame"])
        if frame is None:
            return

        # Redimensionar para rendimiento (max 640px ancho)
        h, w = frame.shape[:2]
        max_w = 640
        if w > max_w:
            scale = max_w / w
            frame = cv2.resize(frame, (max_w, int(h * scale)))

        processed = process_frame_with_hands(frame, current_effect, current_intensity)
        result_data = encode_frame(processed, quality=70)
        emit("processed_frame", {"frame": result_data})
    except Exception as e:
        print(f"Error processing frame: {e}")


@socketio.on("change_effect")
def handle_change_effect(data):
    global current_effect
    effect_key = data.get("effect", "posterize")
    if effect_key in EFFECTS:
        current_effect = effect_key
    emit("state_update", get_state_payload())


@socketio.on("change_intensity")
def handle_change_intensity(data):
    global current_intensity
    current_intensity = max(5, min(200, int(data.get("intensity", 85))))
    emit("state_update", get_state_payload())


@socketio.on("change_mode")
def handle_change_mode(data=None):
    global mode_idx, smoother, rot_smoother, last_box, last_rot_state
    mode_idx = (mode_idx + 1) % len(MODES)
    smoother = SmoothBox()
    rot_smoother = SmoothRotBox()
    last_box = None
    last_rot_state = None
    emit("state_update", get_state_payload())


@socketio.on("toggle_skeleton")
def handle_toggle_skeleton(data=None):
    global show_skeleton
    show_skeleton = not show_skeleton
    emit("state_update", get_state_payload())


@socketio.on("toggle_rotation")
def handle_toggle_rotation(data=None):
    global allow_rotation
    allow_rotation = not allow_rotation
    emit("state_update", get_state_payload())


if __name__ == "__main__":
    print("=" * 60)
    print("  Visor Roto — Web Effects Server (con Hand Tracking)")
    print("  Abre http://localhost:5000 en tu navegador")
    print("  (o usa tu IP local para acceder desde otros dispositivos)")
    print("=" * 60)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
