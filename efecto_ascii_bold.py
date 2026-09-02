"""
efecto_ascii_bold.py -- Visor ASCII Bold: arte ASCII con caracteres gruesos
Ejecutar: python efecto_ascii_bold.py
"""
from effects.ascii_bold import render_ascii_bold
from run_effect import run

def _ascii_bold_effect(patch, intensity):
    return render_ascii_bold(patch)

if __name__ == "__main__":
    run("ascii_bold", _ascii_bold_effect)
