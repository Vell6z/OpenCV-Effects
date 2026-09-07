/**
 * Test/effects.js
 * ---------------
 * Colección de los 13 efectos visuales interactivos de Visor Roto
 * implementados nativamente para Canvas 2D / WebGL a 60 FPS.
 */

export const EFFECTS = {
    posterize: {
        name: "Posterize",
        desc: "Duotone / serigrafía con 4 colores",
        emoji: "🎨",
        apply: applyPosterize
    },
    thermal: {
        name: "Thermal",
        desc: "Cámara térmica simulada (paleta JET)",
        emoji: "🌡️",
        apply: applyThermal
    },
    ascii: {
        name: "ASCII Art",
        desc: "Caracteres ASCII finos",
        emoji: "🔤",
        apply: applyAscii
    },
    ascii_bold: {
        name: "ASCII Bold",
        desc: "ASCII grueso e impactante",
        emoji: "🅰️",
        apply: applyAsciiBold
    },
    edges: {
        name: "Edges",
        desc: "Contornos neón sobre fondo oscuro",
        emoji: "⚡",
        apply: applyEdges
    },
    sketch: {
        name: "Sketch",
        desc: "Grabado a pluma con texturas",
        emoji: "✏️",
        apply: applySketch
    },
    voxel: {
        name: "Voxel",
        desc: "Cubos 3D isométricos azules",
        emoji: "🧊",
        apply: applyVoxel
    },
    distort: {
        name: "Distort",
        desc: "Vidrio esmerilado / blur fuerte",
        emoji: "🌀",
        apply: applyDistort
    },
    combo: {
        name: "Combo",
        desc: "Glitch caótico combinado",
        emoji: "💥",
        apply: applyCombo
    },
    rgb_shift: {
        name: "RGB Shift",
        desc: "Desplazamiento cromático de canales",
        emoji: "🌈",
        apply: applyRgbShift
    },
    slice: {
        name: "Slice",
        desc: "Bandas horizontales desplazadas",
        emoji: "📊",
        apply: applySlice
    },
    pixel_sort: {
        name: "Pixel Sort",
        desc: "Ordenamiento por brillo",
        emoji: "📶",
        apply: applyPixelSort
    },
    noise_block: {
        name: "Noise Block",
        desc: "Bloques de ruido estático",
        emoji: "📺",
        apply: applyNoiseBlock
    },
    data_mosaic: {
        name: "Data Mosaic",
        desc: "Slit-scan, scanlines CRT, aberración y etiquetas ID",
        emoji: "📟",
        apply: applyDataMosaic
    },
    retro_vhs: {
        name: "Retro VHS",
        desc: "Cinta VHS 80s, tracking noise, scanlines CRT y OSD",
        emoji: "📼",
        apply: applyRetroVhs
    },
    digital_avatar: {
        name: "Digital Avatar",
        desc: "Holograma LiDAR 3D, filamentos de luz azul y silueta cuántica",
        emoji: "🌐",
        apply: applyDigitalAvatar
    }
};

// ============================================================================
// 1. POSTERIZE ("Visor Roto" Duotone / Cuatricromía Glitch Dinámico)
// ============================================================================
let posterizeFrameTick = 0;

function applyPosterize(ctx, w, h, intensity) {
    posterizeFrameTick++;
    const imgData = ctx.getImageData(0, 0, w, h);
    const data = imgData.data;
    const numPixels = w * h;

    // 1. Calcular luminancia y ecualizar histograma para contraste de serigrafía puro
    const grays = new Uint8Array(numPixels);
    const hist = new Uint32Array(256);

    for (let i = 0; i < numPixels; i++) {
        const idx = i * 4;
        const g = Math.round(0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2]);
        grays[i] = g;
        hist[g]++;
    }

    // CDF para ecualización
    const cdf = new Uint32Array(256);
    cdf[0] = hist[0];
    for (let i = 1; i < 256; i++) {
        cdf[i] = cdf[i - 1] + hist[i];
    }

    let cdfMin = 0;
    for (let i = 0; i < 256; i++) {
        if (cdf[i] > 0) {
            cdfMin = cdf[i];
            break;
        }
    }

    const lut = new Uint8Array(256);
    const denom = numPixels - cdfMin || 1;
    for (let i = 0; i < 256; i++) {
        lut[i] = Math.round(((cdf[i] - cdfMin) / denom) * 255);
    }

    // 2. Paleta cuatricromía dura (Negro profundo, Magenta neón, Cian eléctrico, Amarillo puro)
    const palette = [
        [15, 12, 18],       // Negro / Sombra profunda
        [230, 25, 190],     // Magenta eléctrico
        [25, 215, 235],     // Cian neón
        [248, 232, 25]      // Amarillo serigrafía
    ];

    for (let i = 0; i < numPixels; i++) {
        const idx = i * 4;
        const eq = lut[grays[i]];
        const pIdx = Math.min(3, Math.floor(eq / 64));
        const color = palette[pIdx];

        data[idx] = color[0];
        data[idx + 1] = color[1];
        data[idx + 2] = color[2];
    }

    ctx.putImageData(imgData, 0, 0);

    // 3. Trama Halftone punteada semi-animada estilo imprenta
    ctx.save();
    ctx.fillStyle = 'rgba(10, 10, 15, 0.22)';
    const spacing = 5;
    const phase = (posterizeFrameTick % 2) * 1;
    for (let y = 0; y < h; y += spacing) {
        for (let x = 0; x < w; x += spacing) {
            if ((Math.floor(x / spacing) + Math.floor(y / spacing) + phase) % 2 === 0) {
                ctx.fillRect(x, y, 2.5, 2.5);
            }
        }
    }
    ctx.restore();

    // 4. Glitch Slice Dinámico (Corte en bandas horizontales con temblor continuo)
    if (intensity > 5) {
        const nSlices = Math.max(4, Math.floor((intensity * 0.35) * 0.45));
        const sliceH = Math.max(3, Math.floor(h / nSlices));
        const maxShift = Math.max(3, Math.floor((intensity * 0.3) * 0.8));

        // Buffer temporal para realizar el corte de bandas
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = w;
        tempCanvas.height = h;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(ctx.canvas, 0, 0);

        for (let y = 0; y < h; y += sliceH) {
            const bh = Math.min(sliceH, h - y);
            // Salto aleatorio por banda
            const shift = Math.round((Math.random() - 0.5) * 2 * maxShift);

            if (Math.abs(shift) > 0) {
                ctx.drawImage(tempCanvas, 0, y, w, bh, shift, y, w, bh);

                // Envolver bordes para que no queden huecos negros
                if (shift > 0) {
                    ctx.drawImage(tempCanvas, w - shift, y, shift, bh, 0, y, shift, bh);
                } else if (shift < 0) {
                    ctx.drawImage(tempCanvas, 0, y, -shift, bh, w + shift, y, -shift, bh);
                }
            }
        }

        // 5. Micro-aberración cromática ocasional (descalce de plancha de color)
        if (Math.random() < 0.65) {
            const glitchY = Math.floor(Math.random() * (h - 20));
            const glitchH = Math.floor(Math.random() * 15 + 6);
            const rgbShift = Math.floor(Math.random() * 6 - 3);

            ctx.save();
            ctx.globalCompositeOperation = 'screen';
            ctx.fillStyle = 'rgba(255, 0, 128, 0.25)';
            ctx.fillRect(rgbShift, glitchY, w, glitchH);
            ctx.fillStyle = 'rgba(0, 230, 255, 0.25)';
            ctx.fillRect(-rgbShift, glitchY, w, glitchH);
            ctx.restore();
        }
    }
}

// ============================================================================
// 2. THERMAL (Cámara térmica simulada con paleta JET)
// ============================================================================
function applyThermal(ctx, w, h, intensity) {
    const imgData = ctx.getImageData(0, 0, w, h);
    const data = imgData.data;

    for (let i = 0; i < data.length; i += 4) {
        const v = (0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]) / 255;
        
        // Mapeo JET (Azul -> Cian -> Verde -> Amarillo -> Rojo)
        let r, g, b;
        if (v < 0.25) {
            r = 0;
            g = 4 * v * 255;
            b = 255;
        } else if (v < 0.5) {
            r = 0;
            g = 255;
            b = (1 - 4 * (v - 0.25)) * 255;
        } else if (v < 0.75) {
            r = 4 * (v - 0.5) * 255;
            g = 255;
            b = 0;
        } else {
            r = 255;
            g = (1 - 4 * (v - 0.75)) * 255;
            b = 0;
        }

        // Ruido leve de sensor térmico
        const noise = (Math.random() - 0.5) * 8;
        data[i] = Math.min(255, Math.max(0, r + noise));
        data[i + 1] = Math.min(255, Math.max(0, g + noise));
        data[i + 2] = Math.min(255, Math.max(0, b + noise));
    }
    ctx.putImageData(imgData, 0, 0);
}

// ============================================================================
// 3. ASCII ART (Fino)
// ============================================================================
const ASCII_CHARS = " .:-=+*#%@";
function applyAscii(ctx, w, h, intensity) {
    const cellSize = 9;
    const cols = Math.floor(w / cellSize);
    const rows = Math.floor(h / cellSize);

    // Muestreo rápido
    const imgData = ctx.getImageData(0, 0, w, h);
    const data = imgData.data;

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, w, h);

    ctx.fillStyle = '#ffffff';
    ctx.font = '700 8px monospace';

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const px = c * cellSize;
            const py = r * cellSize;
            const idx = (py * w + px) * 4;
            const gray = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
            const charIdx = Math.min(ASCII_CHARS.length - 1, Math.floor((gray / 256) * ASCII_CHARS.length));
            const char = ASCII_CHARS[charIdx];
            if (char !== ' ') {
                ctx.fillText(char, px, py + cellSize);
            }
        }
    }
}

// ============================================================================
// 4. ASCII BOLD
// ============================================================================
function applyAsciiBold(ctx, w, h, intensity) {
    const cellSize = 14;
    const cols = Math.floor(w / cellSize);
    const rows = Math.floor(h / cellSize);

    const imgData = ctx.getImageData(0, 0, w, h);
    const data = imgData.data;

    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, w, h);

    ctx.fillStyle = '#36d6e7';
    ctx.font = '900 13px monospace';

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const px = c * cellSize;
            const py = r * cellSize;
            const idx = (py * w + px) * 4;
            const gray = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
            const charIdx = Math.min(ASCII_CHARS.length - 1, Math.floor((gray / 256) * ASCII_CHARS.length));
            const char = ASCII_CHARS[charIdx];
            if (char !== ' ') {
                ctx.fillText(char, px, py + cellSize);
            }
        }
    }
}

// ============================================================================
// 5. EDGES (Siluetas Neón)
// ============================================================================
function applyEdges(ctx, w, h, intensity) {
    const src = ctx.getImageData(0, 0, w, h);
    const s = src.data;
    const out = ctx.createImageData(w, h);
    const d = out.data;

    const thresh = Math.max(20, 100 - intensity * 0.4);

    // Filtro Sobel rápido
    for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
            const idx = (y * w + x) * 4;
            const left = ((y * w + (x - 1)) * 4);
            const right = ((y * w + (x + 1)) * 4);
            const up = (((y - 1) * w + x) * 4);
            const down = (((y + 1) * w + x) * 4);

            const gx = (s[right] - s[left]);
            const gy = (s[down] - s[up]);
            const mag = Math.sqrt(gx * gx + gy * gy);

            if (mag > thresh) {
                d[idx] = 0;
                d[idx + 1] = 230;
                d[idx + 2] = 255;
                d[idx + 3] = 255;
            } else {
                d[idx] = 10;
                d[idx + 1] = 10;
                d[idx + 2] = 18;
                d[idx + 3] = 255;
            }
        }
    }
    ctx.putImageData(out, 0, 0);
}

// ============================================================================
// 6. SKETCH (Grabado / Tinta)
// ============================================================================
function applySketch(ctx, w, h, intensity) {
    const imgData = ctx.getImageData(0, 0, w, h);
    const data = imgData.data;

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const i = (y * w + x) * 4;
            const gray = (data[i] + data[i + 1] + data[i + 2]) / 3;

            // Detección de contraste local
            let edge = 0;
            if (x < w - 1 && y < h - 1) {
                const nextI = (y * w + (x + 1)) * 4;
                const nextGray = (data[nextI] + data[nextI + 1] + data[nextI + 2]) / 3;
                edge = Math.abs(gray - nextGray);
            }

            const val = (gray < 85 || edge > 22) ? 255 : 12;
            data[i] = val;
            data[i + 1] = val;
            data[i + 2] = val;
        }
    }
    ctx.putImageData(imgData, 0, 0);
}

// ============================================================================
// 7. VOXEL (Matriz de cubos isométricos 3D)
// ============================================================================
function applyVoxel(ctx, w, h, intensity) {
    const cellSize = 14;
    const cols = Math.floor(w / cellSize);
    const rows = Math.floor(h / cellSize);

    const imgData = ctx.getImageData(0, 0, w, h);
    const data = imgData.data;

    ctx.fillStyle = '#0a0d16';
    ctx.fillRect(0, 0, w, h);

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const px = c * cellSize;
            const py = r * cellSize;
            const idx = (py * w + px) * 4;
            const brightness = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;

            if (brightness < 30) continue;

            const bVal = Math.min(255, 80 + Math.floor(brightness * 0.7));
            const gVal = Math.min(255, 30 + Math.floor(brightness * 0.3));

            // Cara frontal
            ctx.fillStyle = `rgb(10, ${gVal}, ${bVal})`;
            ctx.fillRect(px, py, cellSize - 1, cellSize - 1);

            // Cara superior
            ctx.fillStyle = `rgb(20, ${Math.min(255, gVal + 35)}, ${Math.min(255, bVal + 45)})`;
            ctx.beginPath();
            ctx.moveTo(px, py);
            ctx.lineTo(px + 4, py - 4);
            ctx.lineTo(px + cellSize + 3, py - 4);
            ctx.lineTo(px + cellSize - 1, py);
            ctx.closePath();
            ctx.fill();

            // Cara lateral
            ctx.fillStyle = `rgb(5, ${Math.max(0, gVal - 20)}, ${Math.max(0, bVal - 30)})`;
            ctx.beginPath();
            ctx.moveTo(px + cellSize - 1, py);
            ctx.lineTo(px + cellSize + 3, py - 4);
            ctx.lineTo(px + cellSize + 3, py + cellSize - 5);
            ctx.lineTo(px + cellSize - 1, py + cellSize - 1);
            ctx.closePath();
            ctx.fill();
        }
    }
}

// ============================================================================
// 8. DISTORT (Vidrio esmerilado / Frosted Glass)
// ============================================================================
function applyDistort(ctx, w, h, intensity) {
    ctx.save();
    const blurPx = Math.max(3, Math.floor(intensity * 0.12));
    ctx.filter = `blur(${blurPx}px) contrast(1.15)`;
    ctx.drawImage(ctx.canvas, 0, 0, w, h);
    ctx.restore();
}

// ============================================================================
// 9. COMBO (Glitch Caótico)
// ============================================================================
function applyCombo(ctx, w, h, intensity) {
    applyRgbShift(ctx, w, h, intensity);
    applySlice(ctx, w, h, intensity);
    applyNoiseBlock(ctx, w, h, intensity * 0.6);
}

// ============================================================================
// 10. RGB SHIFT (Aberración cromática)
// ============================================================================
function applyRgbShift(ctx, w, h, intensity) {
    const shift = Math.max(2, Math.floor(intensity * 0.18));
    const imgData = ctx.getImageData(0, 0, w, h);
    const d = imgData.data;
    const copy = new Uint8ClampedArray(d);

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const idx = (y * w + x) * 4;
            const redX = Math.min(w - 1, x + shift);
            const blueX = Math.max(0, x - shift);

            const redIdx = (y * w + redX) * 4;
            const blueIdx = (y * w + blueX) * 4;

            d[idx] = copy[redIdx];         // Canal Rojo desplazado
            d[idx + 2] = copy[blueIdx + 2]; // Canal Azul desplazado
        }
    }
    ctx.putImageData(imgData, 0, 0);
}

// ============================================================================
// 11. SLICE (Corte en bandas horizontales)
// ============================================================================
function applySlice(ctx, w, h, intensity) {
    const nSlices = Math.floor(4 + (intensity * 0.1));
    for (let i = 0; i < nSlices; i++) {
        const sliceY = Math.floor(Math.random() * h);
        const sliceH = Math.floor(Math.random() * 20 + 8);
        const shiftX = (Math.random() - 0.5) * (intensity * 0.5);

        ctx.drawImage(ctx.canvas, 0, sliceY, w, sliceH, shiftX, sliceY, w, sliceH);
    }
}

// ============================================================================
// 12. PIXEL SORT (Ordenamiento por brillo)
// ============================================================================
function applyPixelSort(ctx, w, h, intensity) {
    const imgData = ctx.getImageData(0, 0, w, h);
    const d = imgData.data;

    const nRows = Math.min(h, Math.floor(intensity * 0.6));
    for (let i = 0; i < nRows; i++) {
        const y = Math.floor(Math.random() * h);
        const startX = Math.floor(Math.random() * (w / 2));
        const len = Math.floor(Math.random() * (w / 3) + 20);
        const endX = Math.min(w, startX + len);

        const pixels = [];
        for (let x = startX; x < endX; x++) {
            const idx = (y * w + x) * 4;
            const b = 0.299 * d[idx] + 0.587 * d[idx + 1] + 0.114 * d[idx + 2];
            pixels.push({ r: d[idx], g: d[idx + 1], b: d[idx + 2], a: d[idx + 3], bVal: b });
        }

        pixels.sort((p1, p2) => p1.bVal - p2.bVal);

        for (let x = startX; x < endX; x++) {
            const idx = (y * w + x) * 4;
            const p = pixels[x - startX];
            d[idx] = p.r;
            d[idx + 1] = p.g;
            d[idx + 2] = p.b;
        }
    }
    ctx.putImageData(imgData, 0, 0);
}

// ============================================================================
// 13. NOISE BLOCK (Bloques de estática)
// ============================================================================
function applyNoiseBlock(ctx, w, h, intensity) {
    const nBlocks = Math.floor(3 + (intensity * 0.08));
    for (let i = 0; i < nBlocks; i++) {
        const bx = Math.random() * w;
        const by = Math.random() * h;
        const bw = Math.random() * 60 + 20;
        const bh = Math.random() * 30 + 10;

        const noiseImg = ctx.createImageData(Math.floor(bw), Math.floor(bh));
        const nd = noiseImg.data;
        for (let j = 0; j < nd.length; j += 4) {
            const val = Math.random() > 0.5 ? 255 : 0;
            nd[j] = val;
            nd[j + 1] = val;
            nd[j + 2] = val;
            nd[j + 3] = 200;
        }
        ctx.putImageData(noiseImg, bx, by);
    }
}

// ============================================================================
// 14. DATA MOSAIC (Slit-Scan, Aberración Cromática, CRT Scanlines & ID Tags)
// ============================================================================
let dataMosaicTick = 0;

function applyDataMosaic(ctx, w, h, intensity) {
    dataMosaicTick++;
    const normInt = Math.max(0.1, intensity / 100);

    // 1. Efecto Slit-Scan horizontal (arrastre de color en franjas como en la referencia)
    const numStreaks = Math.floor(4 + normInt * 8);
    for (let i = 0; i < numStreaks; i++) {
        const sy = Math.floor(((Math.sin(dataMosaicTick * 0.04 + i * 1.5) * 0.5 + 0.5) * (h - 20)));
        const sh = Math.max(3, Math.floor(8 + (i % 3) * 6));
        const sx = Math.floor(((i * 79) % w) * 0.7 + w * 0.15);

        if (i % 2 === 0) {
            // Arrastre hacia el borde izquierdo
            ctx.drawImage(ctx.canvas, sx, sy, 2, sh, 0, sy, sx, sh);
        } else {
            // Arrastre hacia el borde derecho
            ctx.drawImage(ctx.canvas, sx, sy, 2, sh, sx, sy, w - sx, sh);
        }
    }

    // 2. Aberración cromática (RGB split) + sobreexposición magenta en altas luces
    const imgData = ctx.getImageData(0, 0, w, h);
    const d = imgData.data;
    const copy = new Uint8ClampedArray(d);
    const shift = Math.max(2, Math.floor(normInt * 7));

    for (let y = 0; y < h; y += 2) {
        const row = y * w;
        for (let x = 0; x < w; x++) {
            const idx = (row + x) * 4;
            const rx = Math.min(w - 1, x + shift);
            const bx = Math.max(0, x - shift);
            const rIdx = (row + rx) * 4;
            const bIdx = (row + bx) * 4;

            let r = copy[rIdx];
            let g = copy[idx + 1];
            let b = copy[bIdx + 2];

            // Tinte etéreo magenta/rosado en áreas claras (fondo estilo glitch art)
            const lum = 0.299 * r + 0.587 * g + 0.114 * b;
            if (lum > 130) {
                const boost = (lum - 130) * 0.35 * normInt;
                r = Math.min(255, r + boost * 1.3);
                g = Math.max(0, g - boost * 0.25);
                b = Math.min(255, b + boost * 0.85);
            }

            d[idx] = r;
            d[idx + 1] = g;
            d[idx + 2] = b;

            if (y + 1 < h) {
                const nextIdx = ((y + 1) * w + x) * 4;
                d[nextIdx] = r;
                d[nextIdx + 1] = g;
                d[nextIdx + 2] = b;
            }
        }
    }
    ctx.putImageData(imgData, 0, 0);

    // 3. Parches modulares con textura CRT scanlines, tono cobrizo y etiquetas de ID
    const patches = [
        { rx: 0.20, ry: 0.22, rw: 0.36, rh: 0.58, id: 'ID_4550', tint: 'warm' },
        { rx: 0.58, ry: 0.10, rw: 0.28, rh: 0.20, id: 'ID_6739', tint: 'sepia' },
        { rx: 0.60, ry: 0.44, rw: 0.25, rh: 0.18, id: 'ID_ASS0', tint: 'warm' },
        { rx: 0.16, ry: 0.86, rw: 0.20, rh: 0.09, id: 'ID_04.07', tint: 'dark' },
        { rx: 0.02, ry: 0.34, rw: 0.14, rh: 0.14, id: 'ID_239.4', tint: 'cyan' }
    ];

    ctx.save();
    patches.forEach((p, idx) => {
        const px = Math.floor(p.rx * w);
        const py = Math.floor(p.ry * h);
        const pw = Math.floor(p.rw * w);
        const ph = Math.floor(p.rh * h);

        if (pw <= 10 || ph <= 10 || px + pw > w || py + ph > h) return;

        const patchData = ctx.getImageData(px, py, pw, ph);
        const pd = patchData.data;

        // Tinte analógico y textura scanline CRT densa
        for (let pyi = 0; pyi < ph; pyi++) {
            const isScanline = (pyi % 2 === 0);
            const rowOffset = pyi * pw * 4;
            for (let pxi = 0; pxi < pw; pxi++) {
                const i = rowOffset + pxi * 4;
                let pr = pd[i];
                let pg = pd[i + 1];
                let pb = pd[i + 2];

                if (p.tint === 'warm') {
                    const gray = 0.299 * pr + 0.587 * pg + 0.114 * pb;
                    pr = Math.min(255, gray * 1.22 + 22);
                    pg = Math.min(255, gray * 0.94 + 10);
                    pb = Math.max(0, gray * 0.68 - 8);
                } else if (p.tint === 'sepia') {
                    const gray = 0.299 * pr + 0.587 * pg + 0.114 * pb;
                    pr = Math.min(255, gray * 1.15 + 35);
                    pg = Math.min(255, gray * 0.90 + 18);
                    pb = Math.max(0, gray * 0.65);
                }

                if (isScanline) {
                    pr = Math.floor(pr * 0.58);
                    pg = Math.floor(pg * 0.58);
                    pb = Math.floor(pb * 0.58);
                }

                pd[i] = pr;
                pd[i + 1] = pg;
                pd[i + 2] = pb;
            }
        }
        ctx.putImageData(patchData, px, py);

        // Borde nítido sutil blanco/gris
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.75)';
        ctx.lineWidth = 1;
        ctx.strokeRect(px + 0.5, py + 0.5, pw - 1, ph - 1);

        // Cruces HUD en esquinas
        const cross = 4;
        ctx.beginPath();
        ctx.moveTo(px - cross, py); ctx.lineTo(px + cross, py);
        ctx.moveTo(px, py - cross); ctx.lineTo(px, py + cross);
        ctx.moveTo(px + pw - cross, py + ph); ctx.lineTo(px + pw + cross, py + ph);
        ctx.moveTo(px + pw, py + ph - cross); ctx.lineTo(px + pw, py + ph + cross);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.stroke();

        // Etiquetas tipográficas monoespaciadas estilo ID técnico
        ctx.font = "bold 9px 'JetBrains Mono', monospace, sans-serif";
        ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
        ctx.fillText(p.id, px + 5, py - 4 > 10 ? py - 4 : py + 12);

        if (idx === 0) {
            ctx.fillStyle = "rgba(255, 210, 230, 0.85)";
            ctx.font = "7px 'JetBrains Mono', monospace";
            ctx.fillText(`[${Math.round(px)}, ${Math.round(py)}]`, px + 5, py + 22);
        }
    });
    ctx.restore();
}

// ============================================================================
// 15. RETRO VHS (Cinta Analógica 80s, Tracking Noise, Scanlines CRT & VCR OSD)
// ============================================================================
let vhsTick = 0;

function applyRetroVhs(ctx, w, h, intensity) {
    vhsTick++;
    const norm = Math.max(0.1, intensity / 100);

    // 1. Jitter horizontal de cinta VHS (Sync Wobble)
    const wobbleIntensity = Math.max(1, norm * 4);
    const wobbleH = Math.max(6, Math.floor(h / 30));
    for (let sy = 0; sy < h; sy += wobbleH) {
        const offset = Math.sin(vhsTick * 0.15 + sy * 0.05) * wobbleIntensity;
        if (Math.abs(offset) > 0.5) {
            ctx.drawImage(ctx.canvas, 0, sy, w, wobbleH, offset, sy, w, wobbleH);
        }
    }

    // 2. Glitch de salto de cabezal magnético (Tape Tear ocasional)
    if (vhsTick % 45 < 6) {
        const tearY = (Math.sin(vhsTick * 0.08) * 0.5 + 0.5) * (h - 40);
        const tearH = Math.floor(12 + Math.random() * 20);
        const tearShift = (Math.random() - 0.5) * norm * 35;
        ctx.drawImage(ctx.canvas, 0, tearY, w, tearH, tearShift, tearY, w, tearH);
    }

    // 3. Procesamiento de píxeles: NTSC Chroma Bleed, Scanlines CRT & Compresión analógica
    const imgData = ctx.getImageData(0, 0, w, h);
    const d = imgData.data;
    const copy = new Uint8ClampedArray(d);

    const chromaShift = Math.max(2, Math.floor(norm * 9));
    const trackingZoneStart = Math.max(0, h - Math.floor(18 + norm * 16)); // Franja inferior de ruido

    for (let y = 0; y < h; y++) {
        const isScanline = (y % 2 === 0);
        const isTrackingNoise = (y >= trackingZoneStart);
        const row = y * w;

        for (let x = 0; x < w; x++) {
            const idx = (row + x) * 4;

            if (isTrackingNoise) {
                // Nieve estática del cabezal magnético en la base
                const noise = Math.random() > 0.35 ? (Math.random() * 255) : 30;
                d[idx] = noise;
                d[idx + 1] = noise;
                d[idx + 2] = noise;
                continue;
            }

            // Desplazamiento NTSC: el canal rojo se desborda a la derecha, el azul a la izquierda
            const redX = Math.min(w - 1, x + chromaShift);
            const blueX = Math.max(0, x - Math.floor(chromaShift * 0.6));
            const rIdx = (row + redX) * 4;
            const bIdx = (row + blueX) * 4;

            let r = copy[rIdx];
            let g = copy[idx + 1];
            let b = copy[bIdx + 2];

            // Tinte cálido analógico y compresión de negros VHS (elevated blacks)
            r = Math.min(255, r * 1.08 + 12);
            g = Math.min(255, g * 1.02 + 8);
            b = Math.max(0, b * 0.90 + 10);

            // Grano fino analógico
            if (Math.random() < 0.05) {
                const grain = (Math.random() - 0.5) * 40 * norm;
                r = Math.min(255, Math.max(0, r + grain));
                g = Math.min(255, Math.max(0, g + grain));
                b = Math.min(255, Math.max(0, b + grain));
            }

            // Scanlines de monitor CRT entrelazado
            if (isScanline) {
                r *= 0.72;
                g *= 0.72;
                b *= 0.72;
            }

            d[idx] = r;
            d[idx + 1] = g;
            d[idx + 2] = b;
        }
    }
    ctx.putImageData(imgData, 0, 0);

    // 4. OSD Vintage de Videocámara 80s (On Screen Display)
    ctx.save();
    const fontSize = Math.max(11, Math.floor(w * 0.038));
    ctx.font = `bold ${fontSize}px 'JetBrains Mono', monospace, sans-serif`;
    ctx.textBaseline = 'top';

    // Sombra negra sólida de OSD analógico
    ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 2;
    ctx.shadowBlur = 0;

    // PLAY ▶ parpadeante en verde fósforo VCR
    const showPlay = Math.floor(vhsTick / 28) % 2 === 0;
    if (showPlay) {
        ctx.fillStyle = '#55ff77';
        ctx.fillText('PLAY ▶', 18, 16);
    }

    // SP (Standard Play) en la esquina superior derecha
    ctx.fillStyle = '#ffffff';
    const spText = 'SP';
    const spWidth = ctx.measureText(spText).width;
    ctx.fillText(spText, w - spWidth - 18, 16);

    // Fecha 80s y reloj transcurriendo en la esquina inferior izquierda
    const dateText = 'OCT. 26 1989';
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')} PM`;
    
    ctx.fillStyle = '#ffffff';
    ctx.fillText(dateText, 18, h - fontSize * 2.8 - 18);
    ctx.fillText(timeStr, 18, h - fontSize * 1.5 - 18);

    // Canal y tracking OSD en la esquina inferior derecha
    const chText = 'CH 03';
    const chWidth = ctx.measureText(chText).width;
    ctx.fillStyle = '#55ff77';
    ctx.fillText(chText, w - chWidth - 18, h - fontSize * 1.5 - 18);

    ctx.restore();
}

// ============================================================================
// 16. DIGITAL AVATAR (Holograma LiDAR 3D, Filamentos Azules & Fondo Negro)
// ============================================================================
let avatarTick = 0;

function applyDigitalAvatar(ctx, w, h, intensity) {
    avatarTick++;
    const norm = Math.max(0.1, intensity / 100);

    // 1. Obtener imagen actual de la cámara
    const imgData = ctx.getImageData(0, 0, w, h);
    const d = imgData.data;

    // 2. Fondo negro puro absoluto (#000000)
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, w, h);

    // 3. Resolución adaptable para garantizar 60 FPS
    const stepX = w > 900 ? 3 : 2;
    const stepY = 2;
    const depthScale = Math.floor(10 * norm); // Relieve tridimensional según brillo
    const lumThreshold = Math.max(25, 45 - norm * 20); // Umbral de aislamiento de la silueta

    ctx.save();
    ctx.lineWidth = stepX <= 2 ? 1.2 : 1.7;

    // 4. Dibujar filamentos verticales continuos de luz azul holográfica
    for (let x = 0; x < w; x += stepX) {
        for (let y = 0; y < h; y += stepY) {
            const idx = (y * w + x) * 4;
            const r = d[idx];
            const g = d[idx + 1];
            const b = d[idx + 2];
            const lum = 0.299 * r + 0.587 * g + 0.114 * b;

            if (lum > lumThreshold) {
                // Desplazamiento topográfico 3D (las zonas con más luz se extruyen hacia el observador)
                const dispY = y - Math.floor((lum / 255) * depthScale);
                const factor = lum / 255;

                let cr, cg, cb, ca;
                if (factor > 0.72) {
                    // Reflejos especulares y luces altas: Blanco hielo / Perla
                    cr = Math.floor(190 + factor * 65);
                    cg = Math.floor(220 + factor * 35);
                    cb = 255;
                    ca = 0.95;
                } else if (factor > 0.38) {
                    // Cuerpo, rostro y manos: Azul eléctrico vibrante
                    cr = Math.floor(65 + factor * 110);
                    cg = Math.floor(115 + factor * 105);
                    cb = 255;
                    ca = 0.85;
                } else {
                    // Penumbra / bordes lejanos: Azul cobalto profundo
                    cr = Math.floor(25 + factor * 50);
                    cg = Math.floor(45 + factor * 80);
                    cb = Math.floor(170 + factor * 70);
                    ca = 0.65;
                }

                ctx.strokeStyle = `rgba(${cr}, ${cg}, ${cb}, ${ca})`;
                ctx.beginPath();
                ctx.moveTo(x, dispY);
                ctx.lineTo(x, dispY + stepY + 1);
                ctx.stroke();

                // Partículas cuánticas de escaneo flotando alrededor de los bordes del avatar
                if (Math.random() < 0.009 * norm) {
                    const sparkX = x + (Math.random() - 0.5) * 10;
                    const sparkY = dispY + (Math.random() - 0.5) * 10;
                    ctx.fillStyle = 'rgba(190, 235, 255, 0.75)';
                    ctx.fillRect(sparkX, sparkY, 1.5, 1.5);
                }
            }
        }
    }

    // 5. Resplandor (Glow) etéreo holográfico
    ctx.globalCompositeOperation = 'lighter';
    ctx.strokeStyle = 'rgba(60, 140, 255, 0.14)';
    ctx.lineWidth = 3.5;

    for (let x = 0; x < w; x += stepX * 2) {
        for (let y = 0; y < h; y += stepY * 3) {
            const idx = (y * w + x) * 4;
            const lum = 0.299 * d[idx] + 0.587 * d[idx + 1] + 0.114 * d[idx + 2];
            if (lum > lumThreshold + 30) {
                const dispY = y - Math.floor((lum / 255) * depthScale);
                ctx.beginPath();
                ctx.moveTo(x, dispY);
                ctx.lineTo(x, dispY + stepY * 2);
                ctx.stroke();
            }
        }
    }

    ctx.restore();
}
