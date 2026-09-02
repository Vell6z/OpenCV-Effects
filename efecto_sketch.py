"""
efecto_sketch.py -- Sketch/Grabado: líneas finas detalladas sobre fondo negro
Ejecutar: python efecto_sketch.py
"""
from effects.sketch import glitch_sketch
from run_effect import run

if __name__ == "__main__":
    run("sketch", glitch_sketch)
