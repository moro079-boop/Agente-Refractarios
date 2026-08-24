"""Modelo termico 1D radial para ollas de acero (ladles).

Todo el codigo trabaja en unidades SI (m, kg, s, K, W). Las temperaturas
internas son SIEMPRE Kelvin; los grados Celsius aparecen unicamente en las
interfaces de usuario (YAML, CLI, reportes), donde el nombre del campo o de
la variable lleva el sufijo `_C`.
"""

from .units import SIGMA, c2k, k2c
from .materials import Material, MaterialLibrary, load_materials
from .geometry import Layer, Section, Ladle, load_ladle
from .mesh import Mesh, build_mesh
from .boundary import (
    SurfaceBC,
    Adiabatic,
    FixedTemperature,
    Convection,
    LiquidSteelBath,
    EmptyLadleCavity,
    PreheaterBurner,
    AmbientShell,
    wall_to_mouth_view_factor,
)
from .solver import SolverOptions, step, steady_state
from .cycle import Segment, History, run_segments
from .preheat import ReadinessCriterion, PreheatResult, required_preheat_time

__version__ = "0.1.0"

__all__ = [
    "SIGMA", "c2k", "k2c",
    "Material", "MaterialLibrary", "load_materials",
    "Layer", "Section", "Ladle", "load_ladle",
    "Mesh", "build_mesh",
    "SurfaceBC", "Adiabatic", "FixedTemperature", "Convection",
    "LiquidSteelBath", "EmptyLadleCavity", "PreheaterBurner", "AmbientShell",
    "wall_to_mouth_view_factor",
    "SolverOptions", "step", "steady_state",
    "Segment", "History", "run_segments",
    "ReadinessCriterion", "PreheatResult", "required_preheat_time",
]
