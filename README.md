# OpenCV & MediaPipe - Efectos Visuales ("Visor Roto")

Colección de efectos visuales interactivos en tiempo real utilizando OpenCV y MediaPipe Hands / Selfie Segmentation.
Cada efecto detecta la posición de las manos y aplica una transformación visual interactiva dentro del visor formado por los dedos o manos.

## 📦 Requisitos e Instalación

Instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

> **Nota:** Se utiliza `mediapipe==0.10.18` para compatibilidad completa con el pipeline de soluciones (`mp.solutions`).

---

## 🚀 Efectos Disponibles

Ejecuta cualquiera de los siguientes scripts:

| Script | Efecto / Descripción |
|---|---|
| `python efecto_posterize.py` | Posterizado duotone / serigrafía ("Visor Roto") |
| `python efecto_thermal.py` | Cámara térmica simulada (Selfie Segmentation + JET) |
| `python efecto_ascii.py` | Arte ASCII fino en tiempo real |
| `python efecto_ascii_bold.py` | Arte ASCII grueso / bold |
| `python efecto_edges.py` | Contornos / siluetas neón sobre fondo negro |
| `python efecto_sketch.py` | Grabado / sketch a pluma con detalle de texturas |
| `python efecto_voxel.py` | Matriz de cubos 3D isométricos en tonos azules |
| `python efecto_distort.py` | Desenfoque / blur fuerte dentro del visor |
| `python efecto_combo.py` | Glitch caótico combinado |
| `python efecto_rgb_shift.py` | Desplazamiento de canales RGB |
| `python efecto_slice.py` | Corte en bandas horizontales |
| `python efecto_pixel_sort.py` | Pixel sorting por brillo |
| `python efecto_noise_block.py` | Bloques de ruido estático |

---

## 🎮 Controles

Durante la ejecución de cualquier efecto:

- `q` : Salir
- `m` : Cambiar modo de encuadre (Dos manos / Visor de dedos / Zoom centro)
- `r` : Activar/desactivar rotación del visor con el ángulo de las manos
- `+` / `-` : Aumentar o disminuir la intensidad del efecto
- `h` : Mostrar / ocultar esqueleto de detección de manos
- `Espacio` : Pausar / reanudar animación
- `s` : Guardar captura (PNG)
