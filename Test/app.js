/**
 * Test/app.js
 * -----------
 * Controlador principal de Visor Roto Web Serverless.
 * Ejecuta MediaPipe Hands en WebAssembly/GPU, renderiza a 60 FPS
 * y graba video en MP4/WebM directamente en la memoria del dispositivo.
 */

import { EFFECTS } from './effects.js';
import {
    MODES, MODE_LABELS,
    BODY_MODES, BODY_MODE_LABELS,
    SmoothBox, SmoothRotBox,
    landmarksToPx, computeBox,
    rotatedRectFromHands,
    boxFromPose, rotatedRectFromPose,
    drawBrokenGlassBorder, drawHudBorder,
    drawHandSkeleton, drawPoseSkeleton
} from './hand_tracking.js';

(function() {
    'use strict';

    // ---- DOM Elements ----
    const outputCanvas = document.getElementById('outputCanvas');
    const sourceVideo = document.getElementById('sourceVideo');
    const videoPlaceholder = document.getElementById('videoPlaceholder');
    const startCameraBtn = document.getElementById('startCameraBtn');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const cameraSelect = document.getElementById('cameraSelect');
    const flipCameraBtn = document.getElementById('flipCameraBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const intensitySlider = document.getElementById('intensitySlider');
    const intensityValue = document.getElementById('intensityValue');
    const captureBtn = document.getElementById('captureBtn');
    const recordBtn = document.getElementById('recordBtn');
    const recordBtnText = document.getElementById('recordBtnText');
    const recordTimer = document.getElementById('recordTimer');
    const recOverlayBadge = document.getElementById('recOverlayBadge');
    const recOverlayTimer = document.getElementById('recOverlayTimer');
    const fpsBadge = document.getElementById('fpsBadge');
    const targetBtn = document.getElementById('targetBtn');
    const targetIcon = document.getElementById('targetIcon');
    const targetLabel = document.getElementById('targetLabel');
    const modeBtn = document.getElementById('modeBtn');
    const modeIcon = document.getElementById('modeIcon');
    const modeLabel = document.getElementById('modeLabel');
    const rotationBtn = document.getElementById('rotationBtn');
    const rotationBadge = document.getElementById('rotationBadge');
    const skeletonBtn = document.getElementById('skeletonBtn');
    const skeletonBadge = document.getElementById('skeletonBadge');
    const effectsList = document.getElementById('effectsList');
    const effectCount = document.getElementById('effectCount');
    const toast = document.getElementById('toast');

    const ctx = outputCanvas.getContext('2d', { willReadFrequently: true });

    // Patch canvas para aislar el procesamiento de efectos
    const patchCanvas = document.createElement('canvas');
    const patchCtx = patchCanvas.getContext('2d', { willReadFrequently: true });

    // ---- State ----
    let currentEffect = 'posterize';
    let intensity = 85;
    let targetMode = 'hands'; // 'hands' | 'body'
    let modeIndex = 1; // 1 = 'encuadre_dedos'
    let bodyModeIndex = 0; // 0 = 'cuerpo_completo'
    let allowRotation = true;
    let showSkeleton = false;
    let isStreaming = false;
    let currentFacingMode = 'user';
    let availableCameras = [];
    let currentDeviceId = null;

    // Smoothers (Manos y Cuerpo separados para transiciones fluidas)
    const boxSmoother = new SmoothBox(0.35);
    const rotSmoother = new SmoothRotBox(0.35);
    const poseBoxSmoother = new SmoothBox(0.35);
    const poseRotSmoother = new SmoothRotBox(0.35);

    let latestHandResults = null;
    let latestPoseResults = null;

    // FPS Meter
    let frameCount = 0;
    let lastFpsTime = performance.now();

    // MediaRecorder
    let mediaRecorder = null;
    let recordedChunks = [];
    let isRecording = false;
    let recordStartTime = 0;
    let recordTimerInterval = null;

    // ---- Initialize Effects UI ----
    function renderEffectsCatalog() {
        const keys = Object.keys(EFFECTS);
        effectCount.textContent = keys.length;
        effectsList.innerHTML = '';

        keys.forEach(key => {
            const ef = EFFECTS[key];
            const card = document.createElement('div');
            card.className = `effect-card ${key === currentEffect ? 'active' : ''}`;
            card.id = `card_${key}`;
            card.innerHTML = `
                <span class="effect-card__emoji">${ef.emoji}</span>
                <div class="effect-card__info">
                    <span class="effect-card__name">${ef.name}</span>
                    <span class="effect-card__desc">${ef.desc}</span>
                </div>
            `;
            card.addEventListener('click', () => {
                currentEffect = key;
                document.querySelectorAll('.effect-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');
                showToast(`${ef.emoji} ${ef.name}`);
            });
            effectsList.appendChild(card);
        });
    }

    // ---- MediaPipe Setup (Hands & Pose) ----
    let hands = null;
    let pose = null;
    function initMediaPipe() {
        if (window.Hands) {
            hands = new window.Hands({
                locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
            });

            hands.setOptions({
                maxNumHands: 2,
                modelComplexity: 0, // 0 = Lite (Optimizado para 60 FPS en móviles)
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            hands.onResults(onHandResults);
        } else {
            console.warn('MediaPipe Hands script not loaded yet.');
        }

        if (window.Pose) {
            pose = new window.Pose({
                locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
            });

            pose.setOptions({
                modelComplexity: 0, // 0 = Lite (Ultra rápido 60 FPS)
                smoothLandmarks: true,
                enableSegmentation: false,
                smoothSegmentation: false,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            pose.onResults(onPoseResults);
        } else {
            console.warn('MediaPipe Pose script not loaded yet.');
        }
    }

    function onHandResults(results) {
        latestHandResults = results;
    }

    function onPoseResults(results) {
        latestPoseResults = results;
    }

    // ---- Camera Streaming ----
    async function enumerateCameras() {
        try {
            if (!navigator.mediaDevices?.enumerateDevices) return;
            const devices = await navigator.mediaDevices.enumerateDevices();
            availableCameras = devices.filter(d => d.kind === 'videoinput');

            cameraSelect.innerHTML = '';
            availableCameras.forEach((cam, i) => {
                const opt = document.createElement('option');
                opt.value = cam.deviceId;
                opt.textContent = cam.label || `Cámara ${i + 1}`;
                cameraSelect.appendChild(opt);
            });

            if (currentDeviceId) cameraSelect.value = currentDeviceId;
        } catch (e) {
            console.warn('Error enumerating cameras:', e);
        }
    }

    async function startCamera(deviceId = null, facingMode = null) {
        try {
            if (sourceVideo.srcObject) {
                sourceVideo.srcObject.getTracks().forEach(t => t.stop());
            }

            const constraints = {
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                },
                audio: false
            };

            if (deviceId) constraints.video.deviceId = { exact: deviceId };
            else if (facingMode) constraints.video.facingMode = facingMode;
            else constraints.video.facingMode = currentFacingMode;

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            sourceVideo.srcObject = stream;

            const activeTrack = stream.getVideoTracks()[0];
            if (activeTrack) {
                const settings = activeTrack.getSettings();
                currentDeviceId = settings.deviceId || deviceId;
                currentFacingMode = settings.facingMode || facingMode || 'user';
            }

            sourceVideo.onloadedmetadata = () => {
                outputCanvas.width = sourceVideo.videoWidth || 640;
                outputCanvas.height = sourceVideo.videoHeight || 480;

                videoPlaceholder.classList.add('hidden');
                statusDot.classList.add('active');
                statusText.textContent = 'En vivo (60 FPS)';
                isStreaming = true;

                enumerateCameras();
                startRenderLoop();
            };
        } catch (err) {
            console.error('Camera error:', err);
            showToast('⚠️ No se pudo acceder a la cámara: ' + err.message);
        }
    }

    // ---- 60 FPS Render Loop ----
    let isLoopRunning = false;
    let frameCounter = 0;

    function startRenderLoop() {
        if (isLoopRunning) return;
        isLoopRunning = true;

        async function loop() {
            if (!isStreaming) {
                requestAnimationFrame(loop);
                return;
            }

            const w = outputCanvas.width;
            const h = outputCanvas.height;

            // 1. Dibujar el fotograma original de la cámara
            ctx.drawImage(sourceVideo, 0, 0, w, h);

            // 2. Enviar a MediaPipe según el objetivo activo (alternado cada 2 frames para 60 FPS)
            frameCounter++;
            if (targetMode === 'hands') {
                if (hands && (frameCounter % 2 === 0)) {
                    await hands.send({ image: sourceVideo });
                }
                processHandFrame(w, h);
            } else {
                if (pose && (frameCounter % 2 === 0)) {
                    await pose.send({ image: sourceVideo });
                }
                processBodyFrame(w, h);
            }

            // 3. Medidor de FPS
            calculateFPS();

            requestAnimationFrame(loop);
        }

        requestAnimationFrame(loop);
    }

    function processHandFrame(w, h) {
        const mode = MODES[modeIndex];
        const useRotation = allowRotation && mode === 'encuadre_dedos';

        let box = null;
        let rotState = null;

        if (latestHandResults && latestHandResults.multiHandLandmarks?.length) {
            const handsPx = latestHandResults.multiHandLandmarks.map(lm => landmarksToPx(lm, w, h));

            if (useRotation) {
                const rawRot = rotatedRectFromHands(handsPx, w, h);
                if (rawRot) rotState = rotSmoother.update(rawRot);
            } else {
                const rawBox = computeBox(mode, handsPx, w, h);
                if (rawBox) box = boxSmoother.update(rawBox);
            }

            // Esqueleto debug de manos
            if (showSkeleton) {
                drawHandSkeleton(ctx, latestHandResults.multiHandLandmarks, w, h);
            }
        } else {
            rotState = rotSmoother.state;
            box = boxSmoother.box;
        }

        // ---- Renderizar Efecto dentro del Visor ----
        const effect = EFFECTS[currentEffect] || EFFECTS.posterize;

        if (useRotation && rotState) {
            const [cx, cy, rw, rh, angle] = rotState;
            const irw = Math.max(20, Math.round(rw));
            const irh = Math.max(20, Math.round(rh));

            patchCanvas.width = irw;
            patchCanvas.height = irh;

            // Extraer y alinear el parche rotado
            patchCtx.save();
            patchCtx.translate(irw / 2, irh / 2);
            patchCtx.rotate(-angle * Math.PI / 180);
            patchCtx.drawImage(outputCanvas, -cx, -cy);
            patchCtx.restore();

            // Aplicar efecto sobre el parche
            effect.apply(patchCtx, irw, irh, intensity);

            // Pegar el parche rotado en el lienzo principal
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(angle * Math.PI / 180);
            ctx.drawImage(patchCanvas, -irw / 2, -irh / 2);
            ctx.restore();

            // Dibujar borde estilo vidrio roto
            drawBrokenGlassBorder(ctx, cx, cy, irw, irh, angle);

        } else if (box) {
            const [x1, y1, x2, y2] = box;
            const bw = Math.max(20, x2 - x1);
            const bh = Math.max(20, y2 - y1);

            patchCanvas.width = bw;
            patchCanvas.height = bh;

            // Copiar región del visor
            patchCtx.drawImage(outputCanvas, x1, y1, bw, bh, 0, 0, bw, bh);

            // Aplicar efecto
            effect.apply(patchCtx, bw, bh, intensity);

            // Pegar de vuelta
            ctx.drawImage(patchCanvas, x1, y1);

            // Marco HUD
            drawHudBorder(ctx, x1, y1, x2, y2);
        }
    }

    function processBodyFrame(w, h) {
        const mode = BODY_MODES[bodyModeIndex];
        const useRotation = allowRotation;

        let box = null;
        let rotState = null;

        if (latestPoseResults && latestPoseResults.poseLandmarks?.length) {
            const lm = latestPoseResults.poseLandmarks;

            if (useRotation) {
                const rawRot = rotatedRectFromPose(lm, w, h, mode);
                if (rawRot) rotState = poseRotSmoother.update(rawRot);
            } else {
                const rawBox = boxFromPose(lm, w, h, mode);
                if (rawBox) box = poseBoxSmoother.update(rawBox);
            }

            // Esqueleto debug del cuerpo
            if (showSkeleton) {
                drawPoseSkeleton(ctx, lm, w, h);
            }
        } else {
            rotState = poseRotSmoother.state;
            box = poseBoxSmoother.box;
        }

        // ---- Renderizar Efecto Encerrando a la Persona ----
        const effect = EFFECTS[currentEffect] || EFFECTS.posterize;

        if (useRotation && rotState) {
            const [cx, cy, rw, rh, angle] = rotState;
            const irw = Math.max(20, Math.round(rw));
            const irh = Math.max(20, Math.round(rh));

            patchCanvas.width = irw;
            patchCanvas.height = irh;

            // Extraer y alinear el parche rotado centrado en la persona
            patchCtx.save();
            patchCtx.translate(irw / 2, irh / 2);
            patchCtx.rotate(-angle * Math.PI / 180);
            patchCtx.drawImage(outputCanvas, -cx, -cy);
            patchCtx.restore();

            // Aplicar efecto glitch en la región del cuerpo
            effect.apply(patchCtx, irw, irh, intensity);

            // Pegar de vuelta con rotación natural según la postura
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(angle * Math.PI / 180);
            ctx.drawImage(patchCanvas, -irw / 2, -irh / 2);
            ctx.restore();

            // Borde fracturado cyberpunk encerrando a la persona
            drawBrokenGlassBorder(ctx, cx, cy, irw, irh, angle);

        } else if (box) {
            const [x1, y1, x2, y2] = box;
            const bw = Math.max(20, x2 - x1);
            const bh = Math.max(20, y2 - y1);

            patchCanvas.width = bw;
            patchCanvas.height = bh;

            // Copiar región del cuerpo de la persona
            patchCtx.drawImage(outputCanvas, x1, y1, bw, bh, 0, 0, bw, bh);

            // Aplicar efecto
            effect.apply(patchCtx, bw, bh, intensity);

            // Pegar de vuelta
            ctx.drawImage(patchCanvas, x1, y1);

            // Marco HUD delimitador
            drawHudBorder(ctx, x1, y1, x2, y2);
        }
    }

    function calculateFPS() {
        frameCount++;
        const now = performance.now();
        const elapsed = (now - lastFpsTime) / 1000;
        if (elapsed >= 1.0) {
            const fps = Math.round(frameCount / elapsed);
            fpsBadge.textContent = `${fps} FPS`;
            frameCount = 0;
            lastFpsTime = now;
        }
    }

    // ---- MediaRecorder (Grabación de Video en Memoria) ----
    function getBestMimeType() {
        const types = [
            'video/mp4;codecs=avc1',
            'video/mp4',
            'video/webm;codecs=h264',
            'video/webm;codecs=vp9',
            'video/webm'
        ];
        for (const t of types) {
            if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t;
        }
        return '';
    }

    function toggleRecording() {
        if (!isStreaming) {
            showToast('⚠️ Inicia la cámara antes de grabar');
            return;
        }
        if (isRecording) stopRecording();
        else startRecording();
    }

    function startRecording() {
        if (!outputCanvas.captureStream) {
            showToast('⚠️ Grabación no soportada en este navegador');
            return;
        }

        try {
            const mimeType = getBestMimeType();
            const stream = outputCanvas.captureStream(60);
            recordedChunks = [];

            mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

            mediaRecorder.ondataavailable = (e) => {
                if (e.data?.size > 0) recordedChunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
                const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
                const blob = new Blob(recordedChunks, { type: mimeType || 'video/webm' });
                
                if (blob.size === 0) return;

                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `visor_roto_${Date.now()}.${ext}`;
                document.body.appendChild(a);
                a.click();
                setTimeout(() => {
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }, 2000);

                showToast('💾 Video guardado en tu memoria');
            };

            mediaRecorder.start(200);
            isRecording = true;
            recordBtn.classList.add('is-recording');
            recOverlayBadge.classList.add('active');
            recordBtnText.textContent = 'Detener';
            startTimer();
            showToast('🔴 Grabando video a 60 FPS...');
        } catch (err) {
            console.error('Record error:', err);
            showToast('⚠️ Error al grabar: ' + err.message);
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        isRecording = false;
        recordBtn.classList.remove('is-recording');
        recOverlayBadge.classList.remove('active');
        recordBtnText.textContent = 'Grabar';
        stopTimer();
    }

    function startTimer() {
        recordStartTime = Date.now();
        updateTimer();
        recordTimerInterval = setInterval(updateTimer, 1000);
    }

    function updateTimer() {
        const sec = Math.floor((Date.now() - recordStartTime) / 1000);
        const m = String(Math.floor(sec / 60)).padStart(2, '0');
        const s = String(sec % 60).padStart(2, '0');
        const str = `${m}:${s}`;
        recOverlayTimer.textContent = str;
        recordTimer.textContent = str;
        recordTimer.style.display = 'inline';
    }

    function stopTimer() {
        clearInterval(recordTimerInterval);
        recordTimer.style.display = 'none';
    }

    // ---- Event Listeners ----
    startCameraBtn.addEventListener('click', () => startCamera(null, 'user'));

    captureBtn.addEventListener('click', () => {
        if (!isStreaming) return;
        const link = document.createElement('a');
        link.download = `visor_roto_foto_${Date.now()}.jpg`;
        link.href = outputCanvas.toDataURL('image/jpeg', 0.95);
        link.click();
        showToast('📸 Foto guardada en tu dispositivo');
    });

    recordBtn.addEventListener('click', toggleRecording);

    intensitySlider.addEventListener('input', () => {
        intensity = parseInt(intensitySlider.value, 10);
        intensityValue.textContent = intensity;
    });

    // Objetivo: Manos vs Cuerpo
    function setTargetMode(newMode) {
        targetMode = newMode;
        if (targetMode === 'body') {
            targetBtn.classList.add('active');
            targetIcon.textContent = '🧍';
            targetLabel.textContent = 'Cuerpo';
            modeIcon.textContent = '👤';
            modeLabel.textContent = BODY_MODE_LABELS[BODY_MODES[bodyModeIndex]];
            showToast('🧍 Objetivo: Detección de Persona / Cuerpo');
        } else {
            targetBtn.classList.add('active');
            targetIcon.textContent = '🖐️';
            targetLabel.textContent = 'Manos';
            modeIcon.textContent = '🎯';
            modeLabel.textContent = MODE_LABELS[MODES[modeIndex]];
            showToast('🖐️ Objetivo: Detección de Manos');
        }
    }

    targetBtn.addEventListener('click', () => {
        setTargetMode(targetMode === 'hands' ? 'body' : 'hands');
    });

    modeBtn.addEventListener('click', () => {
        if (targetMode === 'hands') {
            modeIndex = (modeIndex + 1) % MODES.length;
            modeLabel.textContent = MODE_LABELS[MODES[modeIndex]];
            showToast(`🖐️ Encuadre: ${MODE_LABELS[MODES[modeIndex]]}`);
        } else {
            bodyModeIndex = (bodyModeIndex + 1) % BODY_MODES.length;
            modeLabel.textContent = BODY_MODE_LABELS[BODY_MODES[bodyModeIndex]];
            showToast(`🧍 Encuadre: ${BODY_MODE_LABELS[BODY_MODES[bodyModeIndex]]}`);
        }
    });

    rotationBtn.addEventListener('click', () => {
        allowRotation = !allowRotation;
        rotationBtn.classList.toggle('active', allowRotation);
        rotationBadge.textContent = allowRotation ? 'ON' : 'OFF';
        showToast(`🔄 Rotación: ${allowRotation ? 'ON' : 'OFF'}`);
    });

    skeletonBtn.addEventListener('click', () => {
        showSkeleton = !showSkeleton;
        skeletonBtn.classList.toggle('active', showSkeleton);
        skeletonBadge.textContent = showSkeleton ? 'ON' : 'OFF';
        showToast(`🦴 Esqueleto: ${showSkeleton ? 'ON' : 'OFF'}`);
    });

    flipCameraBtn.addEventListener('click', () => {
        currentFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
        startCamera(null, currentFacingMode);
        showToast(currentFacingMode === 'user' ? '🤳 Cámara frontal' : '📷 Cámara trasera');
    });

    cameraSelect.addEventListener('change', () => {
        const id = cameraSelect.value;
        if (id) startCamera(id, null);
    });

    fullscreenBtn.addEventListener('click', () => {
        const container = document.getElementById('videoContainer');
        if (!document.fullscreenElement) {
            container.requestFullscreen?.() || container.webkitRequestFullscreen?.();
        } else {
            document.exitFullscreen?.() || document.webkitExitFullscreen?.();
        }
    });

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
        if (e.key === 't') targetBtn.click();
        else if (e.key === 's') captureBtn.click();
        else if (e.key === 'v') recordBtn.click();
        else if (e.key === 'm') modeBtn.click();
        else if (e.key === 'r') rotationBtn.click();
        else if (e.key === 'h') skeletonBtn.click();
        else if (e.key === 'f') fullscreenBtn.click();
    });

    // Toast
    let toastTimer = null;
    function showToast(msg) {
        toast.textContent = msg;
        toast.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove('show'), 2000);
    }

    // Init
    renderEffectsCatalog();
    initMediaPipe();
})();
