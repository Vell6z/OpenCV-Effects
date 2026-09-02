"""
run_effect.py
-------------
Loop principal compartido. Cada script de efecto lo importa y llama a
run(effect_name, process_func, needs_segmentation) para arrancar.

Esto evita duplicar el loop de cámara + tracking en cada archivo de efecto.
"""

import cv2
import mediapipe as mp
import time
import os

from config import (
    CAM_INDEX, FRAME_W, FRAME_H, OUTPUT_DIR,
    DEFAULT_MODE_INDEX, DEFAULT_INTENSITY,
    SHOW_HAND_SKELETON, ALLOW_ROTATION,
)
from hand_tracking import (
    SmoothBox, SmoothRotBox, landmarks_to_px,
    rotated_rect_from_hands, get_rotated_patch, paste_rotated_patch,
    draw_broken_glass_border, compute_box,
    MODES, MODE_LABELS,
)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles
mp_selfie = mp.solutions.selfie_segmentation

os.makedirs(OUTPUT_DIR, exist_ok=True)


def run(effect_name, process_func, needs_segmentation=False, build_source_func=None):
    """Arranca el loop de cámara con un solo efecto fijo.

    Args:
        effect_name: nombre para mostrar en el HUD (ej. "posterize").
        process_func: funcion(patch, intensity) -> patch procesado.
        needs_segmentation: True si el efecto necesita Selfie Segmentation
            (ej. thermal). En ese caso build_source_func es obligatorio.
        build_source_func: funcion(frame_bgr, seg_mask_float) -> frame
            fuente ya transformado (solo para thermal y similares).
    """
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    if not cap.isOpened():
        print("No se pudo abrir la cámara. Revisa el índice CAM_INDEX o los permisos.")
        return

    smoother = SmoothBox()
    rot_smoother = SmoothRotBox()
    mode_idx = DEFAULT_MODE_INDEX
    intensity = DEFAULT_INTENSITY
    paused = False
    show_skeleton = SHOW_HAND_SKELETON
    allow_rotation = ALLOW_ROTATION
    frozen_patch = None
    last_box = None
    last_rot_state = None

    prev_time = time.time()
    fps = 0

    ctx_hands = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    ctx_selfie = mp_selfie.SelfieSegmentation(model_selection=1) if needs_segmentation else None

    try:
        hands = ctx_hands.__enter__()
        selfie_seg = ctx_selfie.__enter__() if ctx_selfie else None

        window_title = f"Visor Roto - {effect_name}"
        print(f"Efecto: {effect_name}")
        print("Controles: q=salir | m=modo | +/-=intensidad | "
              "r=rotacion on/off | h=esqueleto | espacio=pausa | s=guardar")

        while True:
            ok, frame = cap.read()
            if not ok:
                print("No se pudo leer frame de la cámara.")
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            display = frame.copy()
            mode = MODES[mode_idx]
            use_rotation = allow_rotation and mode == "encuadre_dedos"

            # Fuente del frame (normal o transformada, ej. thermal)
            source_frame = frame
            if needs_segmentation and build_source_func and not paused:
                seg_result = selfie_seg.process(rgb)
                seg_mask = seg_result.segmentation_mask
                source_frame = build_source_func(frame, seg_mask)

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

            if use_rotation and rot_state is not None:
                cx, cy, rw, rh, angle = rot_state
                if not paused:
                    patch = get_rotated_patch(source_frame, cx, cy, rw, rh, angle)
                    if patch is not None:
                        processed = process_func(patch, intensity)
                        frozen_patch = processed
                    else:
                        processed = frozen_patch
                else:
                    processed = frozen_patch

                if processed is not None:
                    display, rotated_mask = paste_rotated_patch(
                        display, processed, cx, cy, rw, rh, angle
                    )
                    display = draw_broken_glass_border(display, rotated_mask)

            elif box is not None:
                x1, y1, x2, y2 = box
                x1c, y1c = max(0, x1), max(0, y1)
                x2c, y2c = min(w, x2), min(h, y2)

                if x2c > x1c and y2c > y1c:
                    if not paused:
                        patch = source_frame[y1c:y2c, x1c:x2c].copy()
                        glitched = process_func(patch, intensity)
                        frozen_patch = glitched
                    else:
                        glitched = frozen_patch if frozen_patch is not None else frame[y1c:y2c, x1c:x2c]

                    if glitched is not None and glitched.shape[:2] == (y2c - y1c, x2c - x1c):
                        display[y1c:y2c, x1c:x2c] = glitched

                    cv2.rectangle(display, (x1c, y1c), (x2c, y2c), (0, 255, 255), 2)
                    corner_len = 18
                    corners = [(x1c, y1c, 1, 1), (x2c, y1c, -1, 1),
                               (x1c, y2c, 1, -1), (x2c, y2c, -1, -1)]
                    for cx, cy, dx, dy in corners:
                        cv2.line(display, (cx, cy), (cx + dx * corner_len, cy), (0, 255, 255), 3)
                        cv2.line(display, (cx, cy), (cx, cy + dy * corner_len), (0, 255, 255), 3)

            # ---- HUD ----
            curr_time = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(1e-6, curr_time - prev_time))
            prev_time = curr_time

            hud_lines = [
                f"FPS: {fps:.1f}",
                MODE_LABELS[MODES[mode_idx]] + (" [rotando]" if use_rotation else ""),
                f"Efecto: {effect_name}  (intensidad: {intensity})",
                "PAUSADO" if paused else "",
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

            cv2.imshow(window_title, display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('m'):
                mode_idx = (mode_idx + 1) % len(MODES)
                smoother = SmoothBox()
                rot_smoother = SmoothRotBox()
            elif key == ord(' '):
                paused = not paused
            elif key in (ord('+'), ord('=')):
                intensity = min(200, intensity + 5)
            elif key in (ord('-'), ord('_')):
                intensity = max(5, intensity - 5)
            elif key == ord('h'):
                show_skeleton = not show_skeleton
            elif key == ord('r'):
                allow_rotation = not allow_rotation
            elif key == ord('s'):
                ts = time.strftime("%Y%m%d_%H%M%S")
                out_path = os.path.join(OUTPUT_DIR, f"{effect_name}_{ts}.png")
                cv2.imwrite(out_path, display)
                print(f"Snapshot guardado en: {out_path}")

    finally:
        ctx_hands.__exit__(None, None, None)
        if ctx_selfie:
            ctx_selfie.__exit__(None, None, None)
        cap.release()
        cv2.destroyAllWindows()
