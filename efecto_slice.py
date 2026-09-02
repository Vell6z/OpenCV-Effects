"""
efecto_slice.py -- Slice: corte en bandas horizontales desplazadas
Ejecutar: python efecto_slice.py
"""
from effects.slice import glitch_slice
from run_effect import run

if __name__ == "__main__":
    run("slice", glitch_slice)
