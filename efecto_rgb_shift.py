"""
efecto_rgb_shift.py -- RGB Shift: desplazamiento de canales de color
Ejecutar: python efecto_rgb_shift.py
"""
from effects.rgb_shift import glitch_rgb_shift
from run_effect import run

if __name__ == "__main__":
    run("rgb_shift", glitch_rgb_shift)
