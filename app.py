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
    BODY_MODES, BODY_MODE_LABELS,
    box_from_pose, rotated_rect_from_pose,
)

from config import (
    DEFAULT_MODE_INDEX, DEFAULT_INTENSITY,
    SHOW_HAND_SKELETON, ALLOW_ROTATION,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "visor-roto-secret"
app.config["TEMPLATES_AUTO_RELOAD"] = True
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10 * 1024 * 1024)

# ---- MediaPipe Hands & Pose & Face (se inicializa una vez) ----
mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose
mp_face_detection = mp.solutions.face_detection
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles
mp_selfie = mp.solutions.selfie_segmentation

hands_detector = mp_hands.Hands(
    model_complexity=0,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

pose_detector = mp_pose.Pose(
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

selfie_segmentor = mp_selfie.SelfieSegmentation(model_selection=1)

face_detector = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.5,
)

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
tracking_mode = "hands"  # 'hands' | 'body' | 'face'

# Smoothers (persistentes entre frames para suavizar el cuadro)
smoother = SmoothBox()
rot_smoother = SmoothRotBox()
last_box = None
last_rot_state = None
frame_infer_count = 0
cached_results = None


def decode_frame(data_url):
    """Decodifica un frame JPEG base64 (data URL) a un array BGR de OpenCV."""
    header, encoded = data_url.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame


def encode_frame(frame, quality=60):
    """Codifica un frame BGR de OpenCV a JPEG base64 data URL."""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode(".jpg", frame, encode_params)
    b64 = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def process_frame_with_hands(frame, effect_key, intensity):
    """Procesa un frame: detecta manos, cuerpo o rostro (según tracking_mode),
    y aplica el efecto SOLO dentro del recuadro correspondiente."""
    global last_box, last_rot_state, smoother, rot_smoother, frame_infer_count, cached_results, tracking_mode

    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    frame_infer_count += 1
    # Interleaved tracking: ejecutar red neuronal cada 2 frames si ya hay detección activa
    should_run_mp = (frame_infer_count % 2 != 0) or (last_box is None and last_rot_state is None)

    scale_mp = 240.0 / max(w, 1)
    if scale_mp < 1.0:
        w_mp = 240
        h_mp = max(1, int(h * scale_mp))
        rgb_mp = cv2.resize(rgb, (w_mp, h_mp), interpolation=cv2.INTER_NEAREST)
    else:
        rgb_mp = rgb

    display = frame.copy()
    mode = MODES[mode_idx]
    use_rotation = allow_rotation

    # Fuente del frame (normal o thermal)
    effect_info = EFFECTS.get(effect_key, EFFECTS["posterize"])
    source_frame = frame
    if effect_info["needs_segmentation"] and effect_key == "thermal":
        seg_result = selfie_segmentor.process(rgb_mp)
        seg_mask = cv2.resize(seg_result.segmentation_mask, (w, h), interpolation=cv2.INTER_LINEAR)
        source_frame = build_thermal_frame(frame, seg_mask)

    process_func = effect_info["func"]

    box = last_box
    rot_state = last_rot_state

    if tracking_mode == "body":
        # Detección del cuerpo entero con MediaPipe Pose
        if should_run_mp:
            results = pose_detector.process(rgb_mp)
            cached_results = results
        else:
            results = cached_results if cached_results is not None else pose_detector.process(rgb_mp)

        if results and results.pose_landmarks:
            pose_px = np.array([(int(lm.x * w), int(lm.y * h)) for lm in results.pose_landmarks.landmark])

            if show_skeleton:
                mp_draw.draw_landmarks(
                    display, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
                )

            if use_rotation:
                raw_rot = rotated_rect_from_pose(pose_px, w, h, "cuerpo_completo")
                if raw_rot is not None:
                    rot_state = rot_smoother.update(raw_rot)
                    last_rot_state = rot_state
            else:
                raw_box = box_from_pose(pose_px, w, h, "cuerpo_completo")
                if raw_box is not None:
                    box = smoother.update(raw_box)
                    last_box = box

    elif tracking_mode == "face":
        # Detección de rostro con MediaPipe Face Detection
        face_results = face_detector.process(rgb)
        if face_results and face_results.detections:
            for detection in face_results.detections:
                bbox = detection.location_data.relative_bounding_box
                pad = 15
                fx = max(0, int(bbox.xmin * w) - pad)
                fy = max(0, int(bbox.ymin * h) - pad)
                fw = int(bbox.width * w) + pad * 2
                fh = int(bbox.height * h) + pad * 2
                fx2 = min(w, fx + fw)
                fy2 = min(h, fy + fh)

                if fx2 - fx > 10 and fy2 - fy > 10:
                    face_patch = source_frame[fy:fy2, fx:fx2].copy()
                    try:
                        face_glitched = process_func(face_patch, intensity)
                        if face_glitched is None or face_glitched.shape != face_patch.shape:
                            face_glitched = face_patch
                    except Exception:
                        face_glitched = face_patch

                    display[fy:fy2, fx:fx2] = face_glitched

                    cv2.rectangle(display, (fx, fy), (fx2, fy2), (0, 255, 255), 2)
                    corner_len = 14
                    face_corners = [
                        (fx, fy, 1, 1), (fx2, fy, -1, 1),
                        (fx, fy2, 1, -1), (fx2, fy2, -1, -1),
                    ]
                    for cx_f, cy_f, dx_f, dy_f in face_corners:
                        cv2.line(display, (cx_f, cy_f), (cx_f + dx_f * corner_len, cy_f), (0, 255, 255), 3)
                        cv2.line(display, (cx_f, cy_f), (cx_f, cy_f + dy_f * corner_len), (0, 255, 255), 3)

    else:
        # Detección de manos con MediaPipe Hands
        use_rotation = allow_rotation and mode == "encuadre_dedos"
        if should_run_mp:
            results = hands_detector.process(rgb_mp)
            cached_results = results
        else:
            results = cached_results if cached_results is not None else hands_detector.process(rgb_mp)

        if results and results.multi_hand_landmarks:
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

    # ---- Aplicar efecto en el recuadro (solo para modos hands/body) ----
    if tracking_mode != "face":
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
    TRACKING_LABELS = {"hands": MODE_LABELS[MODES[mode_idx]], "body": "CUERPO COMPLETO", "face": "ROSTRO"}
    hud_label = f"Modo: {TRACKING_LABELS.get(tracking_mode, 'MANOS')}"
    hud_lines = [
        hud_label + (" [rotando]" if (use_rotation and tracking_mode != 'face') else ""),
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
        "tracking_mode": tracking_mode,
        "mode_idx": mode_idx,
        "mode_label": {"hands": MODE_LABELS[MODES[mode_idx]], "body": "Cuerpo completo", "face": "Detección de rostro"}.get(tracking_mode, MODE_LABELS[MODES[mode_idx]]),
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
        # Soporte para datos binarios crudos (bytes) y fallback Base64
        if isinstance(data, (bytes, bytearray)):
            np_arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        elif isinstance(data, dict) and "frame" in data:
            frame = decode_frame(data["frame"])
        elif isinstance(data, str):
            frame = decode_frame(data)
        else:
            return

        if frame is None:
            return

        # Redimensionar para rendimiento (max 480px ancho)
        h, w = frame.shape[:2]
        max_w = 480
        if w > max_w:
            scale = max_w / w
            frame = cv2.resize(frame, (max_w, int(h * scale)), interpolation=cv2.INTER_LINEAR)

        processed = process_frame_with_hands(frame, current_effect, current_intensity)

        # Codificar a JPEG binario puro (sin base64) para máxima velocidad
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 60]
        _, buffer = cv2.imencode(".jpg", processed, encode_params)
        emit("processed_frame", buffer.tobytes())
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


@socketio.on("toggle_body_mode")
def handle_toggle_body_mode(data=None):
    """Cicla entre modos: hands -> body -> face -> hands"""
    global tracking_mode, smoother, rot_smoother, last_box, last_rot_state, cached_results
    CYCLE = ["hands", "body", "face"]
    idx = CYCLE.index(tracking_mode) if tracking_mode in CYCLE else 0
    tracking_mode = CYCLE[(idx + 1) % len(CYCLE)]
    smoother = SmoothBox()
    rot_smoother = SmoothRotBox()
    last_box = None
    last_rot_state = None
    cached_results = None
    emit("state_update", get_state_payload(), broadcast=True)


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


def get_local_ip():
    """Obtiene la IP local de la maquina en la red."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ensure_ssl_certificates():
    """Verifica o genera certificados SSL autofirmados con SAN para localhost e IP local."""
    import os
    cert_path = os.path.join(os.path.dirname(__file__), "cert.pem")
    key_path = os.path.join(os.path.dirname(__file__), "key.pem")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    import datetime
    import ipaddress
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    local_ip = get_local_ip()

    san_list = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]
    if local_ip != "127.0.0.1":
        san_list.append(x509.IPAddress(ipaddress.ip_address(local_ip)))

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CO"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Visor Roto"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Visor Roto Local"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        .sign(key, hashes.SHA256())
    )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    return cert_path, key_path


if __name__ == "__main__":
    import ssl

    cert_file, key_file = ensure_ssl_certificates()
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(cert_file, key_file)

    local_ip = get_local_ip()

    print("=" * 65)
    print("  Visor Roto -- Web Effects Server (HTTPS)")
    print(f"  En tu PC:      https://localhost:5000")
    print(f"  En tu iPhone:  https://{local_ip}:5000")
    print("=" * 65)
    print("  PASO IMPORTANTE EN IPHONE (Safari):")
    print(f"  1. En Safari abre con https:// (https://{local_ip}:5000)")
    print("  2. Toca 'Mostrar detalles' -> 'Visitar este sitio web'")
    print("  3. Permite el acceso a la camara cuando Safari lo pida.")
    print("=" * 65)

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=False,
        allow_unsafe_werkzeug=True,
        ssl_context=ssl_ctx,
    )
