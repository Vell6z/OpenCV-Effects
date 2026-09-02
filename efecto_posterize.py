"""
efecto_posterize.py -- Visor Roto: posterizado duotone/cuatricromía
Ejecutar: python efecto_posterize.py
"""
from effects.posterize import glitch_posterize
from run_effect import run

if __name__ == "__main__":
    run("posterize", glitch_posterize)
