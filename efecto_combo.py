"""
efecto_combo.py -- Glitch caótico: mezcla de slice + pixel sort + rgb shift + ruido
Ejecutar: python efecto_combo.py
"""
from effects.combo import glitch_combo
from run_effect import run

if __name__ == "__main__":
    run("combo", glitch_combo)
