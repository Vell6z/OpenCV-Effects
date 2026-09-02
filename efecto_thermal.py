"""
efecto_thermal.py -- Visor Térmico: cámara térmica simulada
Ejecutar: python efecto_thermal.py
"""
from effects.thermal import build_thermal_frame
from run_effect import run

def _thermal_passthrough(patch, intensity):
    """El frame ya viene coloreado desde build_thermal_frame, solo se pasa."""
    return patch

if __name__ == "__main__":
    run("thermal", _thermal_passthrough,
        needs_segmentation=True,
        build_source_func=build_thermal_frame)
