"""
efecto_ascii.py -- Visor ASCII: arte ASCII en tiempo real
Ejecutar: python efecto_ascii.py
"""
from effects.ascii_art import render_ascii_art
from run_effect import run

def _ascii_effect(patch, intensity):
    return render_ascii_art(patch)

if __name__ == "__main__":
    run("ascii", _ascii_effect)
