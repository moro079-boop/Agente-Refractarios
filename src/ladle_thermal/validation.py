"""Verificacion del solver contra soluciones analiticas.

Un modelo termico solo vale lo que vale su verificacion. Este modulo comprueba
que la implementacion resuelve correctamente la ecuacion que dice resolver,
comparando contra soluciones cerradas donde existen. Es VERIFICACION
(el codigo resuelve bien las ecuaciones), no VALIDACION (las ecuaciones
describen bien la olla real): esa segunda parte requiere datos de planta y esta
documentada en docs/plan_validacion.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .boundary import Adiabatic, Convection, FixedTemperature, cavity_apparent_emissivity, wall_to_mouth_view_factor
from .cycle import Segment, run_segments, uniform_state
from .geometry import Layer, Section
from .materials import Material, PropertyTable
from .mesh import build_mesh
from .solver import SolverOptions, internal_energy, steady_state


@dataclass
class Check:
    name: str
    passed: bool
    error: float
    tolerance: float
    detail: str

    def line(self) -> str:
        mark = "OK  " if self.passed else "FALLA"
        return f"  [{mark}] {self.name:<46s} err={self.error:.3e} (tol {self.tolerance:.0e})  {self.detail}"


def _const_material(name: str, k: float, rho: float, cp: float) -> Material:
    return Material(
        name=name,
        density=rho,
        conductivity=PropertyTable(np.array([300.0]), np.array([k]), f"{name}.k"),
        specific_heat=PropertyTable(np.array([300.0]), np.array([cp]), f"{name}.cp"),
        source="material sintetico de verificacion",
    )


def check_steady_multilayer_planar(tol: float = 1e-4) -> Check:
    """Estacionario en pared plana multicapa contra resistencias en serie."""
    ks = [2.0, 1.5, 0.05, 45.0]
    ls = [0.16, 0.07, 0.015, 0.03]
    mats = [_const_material(f"m{i}", k, 3000.0, 1000.0) for i, k in enumerate(ks)]
    names = tuple(m.name for m in mats)
    section = Section(
        "verif", tuple(Layer(f"c{i}", f"m{i}", l, 12) for i, l in enumerate(ls)),
        "planar", area=1.0,
    )
    mesh = build_mesh(section, names)
    t_hot, t_cold = 1500.0, 350.0
    temp = steady_state(mesh, mats, FixedTemperature(t_hot - 273.15), FixedTemperature(t_cold - 273.15))

    r_total = sum(l / k for l, k in zip(ls, ks))
    q_exact = (t_hot - t_cold) / r_total

    # Flujo numerico a partir del gradiente en la primera celda
    q_num = (t_hot - temp[0]) / (mesh.g_minus[0] / ks[0])
    err = abs(q_num - q_exact) / q_exact
    return Check("Estacionario plano multicapa (flujo)", err < tol, err, tol,
                 f"q={q_num:.1f} vs {q_exact:.1f} W/m2")


def check_steady_cylindrical(tol: float = 2e-3) -> Check:
    """Estacionario en pared cilindrica de una capa contra la formula logaritmica."""
    k, r1, r2, height = 2.0, 1.6, 1.9, 3.0
    mat = _const_material("cyl", k, 3000.0, 1000.0)
    section = Section("verif", (Layer("c", "cyl", r2 - r1, 60),), "cylindrical",
                      inner_radius=r1, height=height)
    mesh = build_mesh(section, ("cyl",))
    t_hot, t_cold = 1500.0, 400.0
    temp = steady_state(mesh, [mat], FixedTemperature(t_hot - 273.15), FixedTemperature(t_cold - 273.15))

    q_exact = 2.0 * math.pi * k * height * (t_hot - t_cold) / math.log(r2 / r1)
    q_num = (t_hot - temp[0]) / (mesh.g_minus[0] / k)
    err = abs(q_num - q_exact) / q_exact

    # Ademas: el perfil debe ser logaritmico
    profile_exact = t_hot - (t_hot - t_cold) * np.log(mesh.x_node / r1) / math.log(r2 / r1)
    err_profile = float(np.max(np.abs(temp - profile_exact))) / (t_hot - t_cold)
    err = max(err, err_profile)
    return Check("Estacionario cilindrico (flujo y perfil)", err < tol, err, tol,
                 f"q={q_num/1000:.1f} vs {q_exact/1000:.1f} kW")


def check_semi_infinite(tol: float = 5e-3) -> Check:
    """Solido semi-infinito con salto de temperatura superficial: solucion de error."""
    k, rho, cp = 2.0, 3000.0, 1000.0
    alpha = k / (rho * cp)
    mat = _const_material("si", k, rho, cp)
    section = Section("verif", (Layer("c", "si", 1.0, 400),), "planar", area=1.0)
    mesh = build_mesh(section, ("si",))

    t_init, t_surface, duration = 300.0, 1300.0, 1800.0
    history = run_segments(
        mesh, [mat], [Segment("salto", duration, FixedTemperature(t_surface - 273.15))],
        uniform_state(mesh, t_init - 273.15), Adiabatic(),
        SolverOptions(dt=2.0, dt_initial=0.02, dt_growth=1.15),
    )
    numeric = history.final_state
    exact = t_surface + (t_init - t_surface) * np.array(
        [math.erf(x / (2.0 * math.sqrt(alpha * duration))) for x in mesh.depth_node]
    )
    depth = 4.0 * math.sqrt(alpha * duration)
    mask = mesh.depth_node <= depth
    err = float(np.max(np.abs(numeric[mask] - exact[mask]))) / (t_surface - t_init)
    return Check("Solido semi-infinito (funcion error)", err < tol, err, tol,
                 f"max dT={err*(t_surface-t_init):.2f} K en {depth*1000:.0f} mm")


def check_energy_conservation(tol: float = 2e-3) -> Check:
    """La energia acumulada debe igualar la integral del flujo entrante."""
    mat = _const_material("en", 1.8, 2800.0, 1050.0)
    section = Section("verif", (Layer("c", "en", 0.25, 60),), "planar", area=2.0)
    mesh = build_mesh(section, ("en",))
    bc = Convection(h=60.0, temperature_C=1200.0)

    history = run_segments(
        mesh, [mat], [Segment("carga", 4 * 3600.0, bc)],
        uniform_state(mesh, 100.0), Adiabatic(),
        SolverOptions(dt=10.0, dt_initial=0.05, dt_growth=1.2),
    )
    energy_in = float(np.trapezoid(history.q_hot, history.times))
    delta_u = (internal_energy(mesh, [mat], history.final_state)
               - internal_energy(mesh, [mat], history.initial_state))
    err = abs(energy_in - delta_u) / abs(delta_u)
    return Check("Conservacion de energia (flujo vs entalpia)", err < tol, err, tol,
                 f"{energy_in/1e6:.2f} vs {delta_u/1e6:.2f} MJ")


def check_lumped_cooling(tol: float = 5e-3) -> Check:
    """Placa delgada con Biot pequeno: decaimiento exponencial con tau = rho*V*cp/(h*A)."""
    k, rho, cp, thickness, h = 45.0, 7850.0, 470.0, 0.01, 12.0
    mat = _const_material("lumped", k, rho, cp)
    section = Section("verif", (Layer("c", "lumped", thickness, 20),), "planar", area=1.0)
    mesh = build_mesh(section, ("lumped",))

    t_init, t_env, duration = 800.0, 300.0, 3000.0
    # Una sola cara convectiva, la otra adiabatica
    history = run_segments(
        mesh, [mat], [Segment("enfria", duration, Convection(h=h, temperature_C=t_env - 273.15))],
        uniform_state(mesh, t_init - 273.15), Adiabatic(),
        SolverOptions(dt=5.0, dt_initial=0.05, dt_growth=1.2),
    )
    tau = rho * thickness * cp / h
    exact = t_env + (t_init - t_env) * math.exp(-duration / tau)
    numeric = float(np.mean(history.final_state))
    err = abs(numeric - exact) / (t_init - t_env)
    biot = h * thickness / k
    return Check("Enfriamiento agrupado (Biot pequeno)", err < tol, err, tol,
                 f"T={numeric-273.15:.2f} vs {exact-273.15:.2f} C, Bi={biot:.4f}")


def check_grid_independence(tol: float = 8e-3) -> Check:
    """Refinar malla y paso de tiempo no debe cambiar el resultado apreciablemente."""
    from .boundary import AmbientShell, EmptyLadleCavity
    from .materials import load_materials

    lib = load_materials()
    names = tuple(lib.names())
    mats = [lib[n] for n in names]

    def hot_face_at(n_mult: int, dt: float) -> float:
        section = Section("w", (
            Layer("trabajo", "alumina_spinel_castable", 0.160, 12 * n_mult, 1.08),
            Layer("seguridad", "high_alumina_brick_70", 0.070, 4 * n_mult),
            Layer("aislante", "microporous_board", 0.015, 2 * n_mult),
            Layer("carcasa", "carbon_steel_shell", 0.030, 2 * n_mult)),
            "cylindrical", inner_radius=1.6, height=3.4)
        mesh = build_mesh(section, names)
        cavity = EmptyLadleCavity.from_section(1.6, 3.75)
        history = run_segments(
            mesh, mats, [Segment("enfria", 3600.0, cavity)],
            uniform_state(mesh, 1400.0), AmbientShell(35.0, 0.8, 3.4),
            SolverOptions(dt=dt, dt_initial=0.1, dt_growth=1.3),
        )
        return float(history.hot_face_C[-1])

    coarse = hot_face_at(1, 60.0)
    fine = hot_face_at(4, 5.0)
    err = abs(coarse - fine) / abs(fine)
    return Check("Independencia de malla y paso de tiempo", err < tol, err, tol,
                 f"{coarse:.1f} vs {fine:.1f} C tras 60 min")


def check_cavity_models_agree(tol: float = 0.15) -> Check:
    """Los dos modelos radiativos independientes de la boca deben coincidir."""
    radius, depth, eps = 1.60, 3.75, 0.85
    view = eps * wall_to_mouth_view_factor(radius, depth)
    mouth = math.pi * radius ** 2
    cavity = 2.0 * math.pi * radius * depth + mouth
    apparent = cavity_apparent_emissivity(eps, mouth, cavity) * mouth / cavity
    err = abs(view - apparent) / apparent
    return Check("Coherencia de los dos modelos de cavidad", err < tol, err, tol,
                 f"factor de vista {view:.4f} vs cavidad {apparent:.4f}")


ALL_CHECKS = (
    check_steady_multilayer_planar,
    check_steady_cylindrical,
    check_semi_infinite,
    check_energy_conservation,
    check_lumped_cooling,
    check_grid_independence,
    check_cavity_models_agree,
)


def run_all(verbose: bool = False) -> list[Check]:
    results = []
    if verbose:
        print("Verificacion del solver contra soluciones analiticas:\n")
    for fn in ALL_CHECKS:
        check = fn()
        results.append(check)
        if verbose:
            print(check.line(), flush=True)
    return results
