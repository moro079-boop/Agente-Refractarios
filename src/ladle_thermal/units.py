"""Constantes fisicas y conversiones. Convencion: SI, temperaturas en Kelvin."""

from __future__ import annotations

import numpy as np

SIGMA = 5.670374419e-8          # Stefan-Boltzmann [W/m2K4]
T0_K = 273.15                   # 0 C en K
GRAVITY = 9.80665               # [m/s2]


def c2k(t_c):
    """Celsius -> Kelvin."""
    return np.asarray(t_c, dtype=float) + T0_K if np.ndim(t_c) else float(t_c) + T0_K


def k2c(t_k):
    """Kelvin -> Celsius."""
    return np.asarray(t_k, dtype=float) - T0_K if np.ndim(t_k) else float(t_k) - T0_K


# --- Propiedades del aire a 1 atm (Incropera, Tabla A.4) ----------------------
# Se usan para las correlaciones de conveccion natural en la carcasa.
_AIR_T = np.array([250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 1000.0])
_AIR_K = np.array([0.0223, 0.0263, 0.0300, 0.0338, 0.0373, 0.0407, 0.0469, 0.0524, 0.0573, 0.0667])
_AIR_NU = np.array([11.44, 15.89, 20.92, 26.41, 32.39, 38.79, 52.69, 68.10, 84.93, 120.5]) * 1e-6
_AIR_PR = np.array([0.720, 0.707, 0.700, 0.690, 0.686, 0.684, 0.685, 0.690, 0.697, 0.726])


def air_properties(t_k: float) -> tuple[float, float, float]:
    """Conductividad [W/mK], viscosidad cinematica [m2/s] y Prandtl del aire."""
    t = float(np.clip(t_k, _AIR_T[0], _AIR_T[-1]))
    return (
        float(np.interp(t, _AIR_T, _AIR_K)),
        float(np.interp(t, _AIR_T, _AIR_NU)),
        float(np.interp(t, _AIR_T, _AIR_PR)),
    )
