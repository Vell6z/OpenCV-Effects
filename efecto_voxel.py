"""
efecto_voxel.py -- Voxel Matrix: cubos 3D azules tipo escultura digital
Ejecutar: python efecto_voxel.py
"""
from effects.voxel import glitch_voxel
from run_effect import run

if __name__ == "__main__":
    run("voxel", glitch_voxel)
