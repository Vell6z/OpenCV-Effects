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
