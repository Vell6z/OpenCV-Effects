/**
 * Test/hand_tracking.js
 * ---------------------
 * Lógica de tracking de manos, suavizado de coordenadas, encuadre
 * trigonométrico y dibujo del borde "vidrio roto" estilo Visor Roto.
 */

// Constantes de tracking
const MIN_BOX_SIZE = 40;
const BOX_PADDING = 25;
const SMOOTHING = 0.35;

export const MODES = ['dos_manos_bbox', 'encuadre_dedos', 'zoom_centro'];
export const MODE_LABELS = {
    dos_manos_bbox: 'Dos manos',
    encuadre_dedos: 'Visor de dedos',
    zoom_centro: 'Zoom centro'
};

/**
 * Suaviza las coordenadas del cuadro (x1, y1, x2, y2) para evitar temblores.
 */
export class SmoothBox {
    constructor(alpha = SMOOTHING) {
        this.alpha = alpha;
        this.box = null;
    }

    update(newBox) {
        if (!newBox) return this.box;
        if (!this.box) {
            this.box = [...newBox];
        } else {
            for (let i = 0; i < 4; i++) {
                this.box[i] = this.alpha * this.box[i] + (1 - this.alpha) * newBox[i];
            }
        }
        return this.box.map(v => Math.round(v));
    }
}

/**
 * Suaviza (cx, cy, w, h, angle) con manejo especial de cruces +-90 grados.
 */
export class SmoothRotBox {
    constructor(alpha = SMOOTHING) {
        this.alpha = alpha;
        this.state = null; // [cx, cy, w, h, angle]
    }

    update(newState) {
        if (!newState) return this.state;
        let [cx, cy, w, h, angle] = newState;

        if (!this.state) {
            this.state = [cx, cy, w, h, angle];
        } else {
            const a = this.alpha;
            let prevAngle = this.state[4];
            let diff = angle - prevAngle;
            if (diff > 90) angle -= 180;
            else if (diff < -90) angle += 180;

            this.state[0] = a * this.state[0] + (1 - a) * cx;
            this.state[1] = a * this.state[1] + (1 - a) * cy;
            this.state[2] = a * this.state[2] + (1 - a) * w;
            this.state[3] = a * this.state[3] + (1 - a) * h;
            this.state[4] = a * prevAngle + (1 - a) * angle;
        }
        return [...this.state];
    }
}

export function landmarksToPx(landmarks, w, h) {
    return landmarks.map(lm => ({
        x: Math.round(lm.x * w),
        y: Math.round(lm.y * h)
    }));
}

function clampBox(x1, y1, x2, y2, w, h) {
    x1 = Math.max(0, Math.min(w - 1, x1));
    y1 = Math.max(0, Math.min(h - 1, y1));
    x2 = Math.max(0, Math.min(w - 1, x2));
    y2 = Math.max(0, Math.min(h - 1, y2));
    if (x2 - x1 < MIN_BOX_SIZE) {
        const cx = Math.floor((x1 + x2) / 2);
        x1 = Math.max(0, cx - Math.floor(MIN_BOX_SIZE / 2));
        x2 = Math.min(w - 1, x1 + MIN_BOX_SIZE);
    }
    if (y2 - y1 < MIN_BOX_SIZE) {
        const cy = Math.floor((y1 + y2) / 2);
        y1 = Math.max(0, cy - Math.floor(MIN_BOX_SIZE / 2));
        y2 = Math.min(h - 1, y1 + MIN_BOX_SIZE);
    }
    return [x1, y1, x2, y2];
}

export function boxFromTwoHands(handsPx, w, h) {
    const allPts = handsPx.flat();
    if (!allPts.length) return null;
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const pt of allPts) {
        if (pt.x < x1) x1 = pt.x;
        if (pt.y < y1) y1 = pt.y;
        if (pt.x > x2) x2 = pt.x;
        if (pt.y > y2) y2 = pt.y;
    }
    return clampBox(x1 - BOX_PADDING, y1 - BOX_PADDING, x2 + BOX_PADDING, y2 + BOX_PADDING, w, h);
}

export function boxFromFingerFrame(handsPxList, w, h) {
    const pts = [];
    for (const hp of handsPxList) {
        if (hp[4]) pts.push(hp[4]); // pulgar
        if (hp[8]) pts.push(hp[8]); // índice
    }
    if (!pts.length) return null;
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const pt of pts) {
        if (pt.x < x1) x1 = pt.x;
        if (pt.y < y1) y1 = pt.y;
        if (pt.x > x2) x2 = pt.x;
        if (pt.y > y2) y2 = pt.y;
    }
    const pad = Math.floor(BOX_PADDING / 2);
    return clampBox(x1 - pad, y1 - pad, x2 + pad, y2 + pad, w, h);
}

export function zoomCenterBox(handsPxList, w, h) {
    const baseBox = boxFromFingerFrame(handsPxList, w, h) || boxFromTwoHands(handsPxList, w, h);
    if (!baseBox) return null;
    const [x1, y1, x2, y2] = baseBox;
    const cx = (x1 + x2) / 2;
    const cy = (y1 + y2) / 2;
    const bw = (x2 - x1) * 0.7;
    const bh = (y2 - y1) * 0.7;
    return clampBox(Math.round(cx - bw / 2), Math.round(cy - bh / 2), Math.round(cx + bw / 2), Math.round(cy + bh / 2), w, h);
}

export function computeBox(mode, handsPx, w, h) {
    if (mode === 'dos_manos_bbox') return boxFromTwoHands(handsPx, w, h);
    if (mode === 'encuadre_dedos') return boxFromFingerFrame(handsPx, w, h);
    if (mode === 'zoom_centro') return zoomCenterBox(handsPx, w, h);
    return boxFromFingerFrame(handsPx, w, h);
}

export function rotatedRectFromHands(handsPxList, w, h) {
    const pts = [];
    for (const hp of handsPxList) {
        if (hp[4]) pts.push(hp[4]);
        if (hp[8]) pts.push(hp[8]);
    }
    if (!pts.length) return null;

    let vecX, vecY;
    if (handsPxList.length >= 2) {
        const c1 = handsPxList[0][0]; // muñeca
        const c2 = handsPxList[1][0];
        vecX = c2.x - c1.x;
        vecY = c2.y - c1.y;
    } else {
        const thumb = handsPxList[0][4];
        const index = handsPxList[0][8];
        vecX = index.x - thumb.x;
        vecY = index.y - thumb.y;
    }

    let angle = Math.atan2(vecY, vecX) * (180 / Math.PI);
    if (angle > 90) angle -= 180;
    else if (angle < -90) angle += 180;

    let sumX = 0, sumY = 0;
    for (const p of pts) {
        sumX += p.x;
        sumY += p.y;
    }
    const cx = sumX / pts.length;
    const cy = sumY / pts.length;

    const rad = angle * (Math.PI / 180);
    const cosT = Math.cos(rad);
    const sinT = Math.sin(rad);

    let minLX = Infinity, maxLX = -Infinity;
    let minLY = Infinity, maxLY = -Infinity;

    for (const p of pts) {
        const rx = p.x - cx;
        const ry = p.y - cy;
        const lx = rx * cosT + ry * sinT;
        const ly = -rx * sinT + ry * cosT;
        if (lx < minLX) minLX = lx;
        if (lx > maxLX) maxLX = lx;
        if (ly < minLY) minLY = ly;
        if (ly > maxLY) maxLY = ly;
    }

    let rectW = Math.max(MIN_BOX_SIZE, (maxLX - minLX) + BOX_PADDING);
    let rectH = Math.max(MIN_BOX_SIZE, (maxLY - minLY) + BOX_PADDING);

    return [cx, cy, rectW, rectH, angle];
}

/**
 * Dibuja un marco estilo vidrio roto cyberpunk con brillo magenta.
 */
export function drawBrokenGlassBorder(ctx, cx, cy, w, h, angleDeg) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angleDeg * Math.PI / 180);

    const hw = w / 2;
    const hh = h / 2;

    ctx.strokeStyle = '#c83ce6';
    ctx.lineWidth = 3;
    ctx.shadowColor = '#c83ce6';
    ctx.shadowBlur = 12;

    // Trazado irregular tipo fractura
    ctx.beginPath();
    const jitter = 5;
    ctx.moveTo(-hw, -hh);
    ctx.lineTo(0 + (Math.random() - 0.5) * jitter, -hh + (Math.random() - 0.5) * jitter);
    ctx.lineTo(hw, -hh);
    ctx.lineTo(hw + (Math.random() - 0.5) * jitter, 0 + (Math.random() - 0.5) * jitter);
    ctx.lineTo(hw, hh);
    ctx.lineTo(0 + (Math.random() - 0.5) * jitter, hh + (Math.random() - 0.5) * jitter);
    ctx.lineTo(-hw, hh);
    ctx.lineTo(-hw + (Math.random() - 0.5) * jitter, 0 + (Math.random() - 0.5) * jitter);
    ctx.closePath();
    ctx.stroke();

    // Grietas sutiles que salen de las esquinas
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(-hw, -hh);
    ctx.lineTo(-hw + 14, -hh + 14);
    ctx.moveTo(hw, -hh);
    ctx.lineTo(hw - 14, -hh + 14);
    ctx.moveTo(hw, hh);
    ctx.lineTo(hw - 14, hh - 14);
    ctx.moveTo(-hw, hh);
    ctx.lineTo(-hw + 14, hh - 14);
    ctx.stroke();

    ctx.restore();
}

/**
 * Dibuja el marco normal rectangular con esquinas estilo HUD.
 */
export function drawHudBorder(ctx, x1, y1, x2, y2) {
    ctx.save();
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 2;
    ctx.shadowColor = '#00e5ff';
    ctx.shadowBlur = 8;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    // Esquinas acentuadas
    ctx.lineWidth = 3;
    const corner = 16;
    ctx.beginPath();
    // Sup Izq
    ctx.moveTo(x1, y1 + corner); ctx.lineTo(x1, y1); ctx.lineTo(x1 + corner, y1);
    // Sup Der
    ctx.moveTo(x2 - corner, y1); ctx.lineTo(x2, y1); ctx.lineTo(x2, y1 + corner);
    // Inf Der
    ctx.moveTo(x2, y2 - corner); ctx.lineTo(x2, y2); ctx.lineTo(x2 - corner, y2);
    // Inf Izq
    ctx.moveTo(x1 + corner, y2); ctx.lineTo(x1, y2); ctx.lineTo(x1, y2 - corner);
    ctx.stroke();
    ctx.restore();
}

/**
 * Dibuja el esqueleto de las manos (landmarks y conexiones).
 */
export function drawHandSkeleton(ctx, landmarksList, w, h) {
    const CONNECTIONS = [
        [0, 1], [1, 2], [2, 3], [3, 4],       // pulgar
        [0, 5], [5, 6], [6, 7], [7, 8],       // índice
        [5, 9], [9, 10], [10, 11], [11, 12],  // medio
        [9, 13], [13, 14], [14, 15], [15, 16],// anular
        [13, 17], [17, 18], [18, 19], [19, 20],// meñique
        [0, 17]                               // palma
    ];

    ctx.save();
    for (const lm of landmarksList) {
        const pts = lm.map(p => ({ x: p.x * w, y: p.y * h }));

        // Conexiones
        ctx.strokeStyle = 'rgba(54, 214, 231, 0.6)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (const [i, j] of CONNECTIONS) {
            ctx.moveTo(pts[i].x, pts[i].y);
            ctx.lineTo(pts[j].x, pts[j].y);
        }
        ctx.stroke();

        // Puntos
        for (let i = 0; i < pts.length; i++) {
            ctx.fillStyle = (i === 4 || i === 8) ? '#ff3366' : '#c83ce6';
            ctx.beginPath();
            ctx.arc(pts[i].x, pts[i].y, (i === 4 || i === 8) ? 4.5 : 3, 0, Math.PI * 2);
            ctx.fill();
        }
    }
    ctx.restore();
}
