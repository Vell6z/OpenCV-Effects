"""
efecto_noise_block.py -- Noise Block: bloques de ruido/estática
Ejecutar: python efecto_noise_block.py
"""
from effects.noise_block import glitch_noise_block
from run_effect import run

if __name__ == "__main__":
    run("noise_block", glitch_noise_block)
