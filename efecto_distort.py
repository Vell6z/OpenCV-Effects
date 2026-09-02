"""
efecto_distort.py -- Distorsión líquida: lente curva + ondulaciones animadas
Ejecutar: python efecto_distort.py
"""
from effects.distort import glitch_distort
from run_effect import run

if __name__ == "__main__":
    run("distort", glitch_distort)
