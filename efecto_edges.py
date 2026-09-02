"""
efecto_edges.py -- Contorno Neon: bordes/siluetas blancos sobre fondo negro
Ejecutar: python efecto_edges.py
"""
from effects.edges import glitch_edges
from run_effect import run

if __name__ == "__main__":
    run("edges", glitch_edges)
