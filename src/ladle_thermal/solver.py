"""Solver 1D transitorio por volumenes finitos, implicito.

Ecuacion resuelta (forma conservativa, coordenadas cilindricas o planas):

    rho(T) * cp(T) * dT/dt = div( k(T) * grad T )

Discretizacion: volumenes finitos, Euler implicito (incondicionalmente
estable), sistema tridiagonal resuelto con el algoritmo de Thomas. Las no
linealidades (k(T), cp(T) y sobre todo la radiacion en las fronteras) se
resuelven con iteraciones de punto fijo dentro de cada paso de tiempo.

Decisiones numericas relevantes:
  - `cp` se evalua en el punto medio (T_old + T_new)/2: da segundo orden en la
    capacidad y conserva mucho mejor la energia que evaluarla en T_new.
  - `k` se evalua en T_new, consistente con el flujo implicito.
  - La resistencia solida de media celda se combina en serie con la pelicula
    superficial, de modo que la temperatura de la CARA (no la del nodo) se
    recupera exactamente. Esto importa: el criterio de 1100 C es sobre la cara
    caliente, no sobre el centro de la primera celda.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .boundary import SurfaceBC
from .materials import Material
from .mesh import Mesh

_INF_R = 1.0e30


@dataclass
class SolverOptions:
    """Parametros numericos."""

    dt: float = 30.0                 # paso de tiempo objetivo [s]
    dt_initial: float | None = 1.0   # primer paso tras un cambio de frontera [s]
    dt_growth: float = 1.35          # factor de crecimiento del paso
    max_iterations: int = 50
    tolerance: float = 1.0e-4        # criterio de convergencia en K
    relaxation: float = 1.0          # <1 para casos radiativos duros
    sample_interval: float | None = None   # intervalo de muestreo de resultados [s]

    def __post_init__(self) -> None:
        if self.dt <= 0:
            raise ValueError("dt debe ser > 0")
        if self.dt_growth < 1.0:
            raise ValueError("dt_growth debe ser >= 1")
        if not 0.0 < self.relaxation <= 1.0:
            raise ValueError("relaxation debe estar en (0, 1]")


@dataclass
class StepResult:
    """Resultado de un paso de tiempo."""

    T: np.ndarray
    hot_surface_K: float
    cold_surface_K: float
    q_hot: float          # [W] positivo = entra calor por la cara caliente
    q_cold: float         # [W] positivo = entra calor por la cara fria
    iterations: int
    converged: bool
    residual: float = 0.0


def tdma(lower: np.ndarray, diag: np.ndarray, upper: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    """Algoritmo de Thomas para sistemas tridiagonales."""
    n = diag.size
    if n == 1:
        return np.array([rhs[0] / diag[0]])
    cp = np.empty(n - 1)
    dp = np.empty(n)
    beta = diag[0]
    cp[0] = upper[0] / beta
    dp[0] = rhs[0] / beta
    for i in range(1, n):
        beta = diag[i] - lower[i] * cp[i - 1]
        if i < n - 1:
            cp[i] = upper[i] / beta
        dp[i] = (rhs[i] - lower[i] * dp[i - 1]) / beta
    x = np.empty(n)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


class _PropertyEvaluator:
    """Evalua k, rho y cp por celda vectorizando por material."""

    def __init__(self, mesh: Mesh, materials: list[Material]):
        self.mesh = mesh
        self.materials = materials
        self._masks = [mesh.mat_index == i for i in range(len(materials))]
        self.rho = np.empty(mesh.n_cells)
        for i, mask in enumerate(self._masks):
            self.rho[mask] = materials[i].density

    def conductivity(self, temp: np.ndarray) -> np.ndarray:
        out = np.empty_like(temp)
        for i, mask in enumerate(self._masks):
            if mask.any():
                out[mask] = self.materials[i].k(temp[mask])
        return out

    def specific_heat(self, temp: np.ndarray) -> np.ndarray:
        out = np.empty_like(temp)
        for i, mask in enumerate(self._masks):
            if mask.any():
                out[mask] = self.materials[i].cp(temp[mask])
        return out


def _face_conductances(
    mesh: Mesh, k_cell: np.ndarray, h_hot: float, h_cold: float
) -> np.ndarray:
    """Conductancias [W/K] en cada una de las n+1 caras."""
    n = mesh.n_cells
    g = np.zeros(n + 1)

    if n > 1:
        r_int = mesh.g_plus[:-1] / k_cell[:-1] + mesh.g_minus[1:] / k_cell[1:] + mesh.contact_R[1:n]
        g[1:n] = 1.0 / r_int

    r_hot = mesh.g_minus[0] / k_cell[0] + (1.0 / (h_hot * mesh.face_area[0]) if h_hot > 0 else _INF_R)
    g[0] = 1.0 / r_hot
    r_cold = mesh.g_plus[-1] / k_cell[-1] + (1.0 / (h_cold * mesh.face_area[-1]) if h_cold > 0 else _INF_R)
    g[n] = 1.0 / r_cold
    return g


def _surface_temperature(t_env: float, t_node: float, g_face: float, h: float, area: float) -> tuple[float, float]:
    """Devuelve (T_superficie [K], q [W]) recuperando la caida en la pelicula."""
    q = g_face * (t_env - t_node)
    if h <= 0:
        return float(t_node), 0.0
    return float(t_env - q / (h * area)), float(q)


def step(
    mesh: Mesh,
    materials: list[Material],
    t_old: np.ndarray,
    dt: float,
    bc_hot: SurfaceBC,
    bc_cold: SurfaceBC,
    t_now: float = 0.0,
    options: SolverOptions | None = None,
    props: _PropertyEvaluator | None = None,
) -> StepResult:
    """Avanza un paso de tiempo implicito con iteraciones de punto fijo."""
    opts = options or SolverOptions()
    props = props or _PropertyEvaluator(mesh, materials)
    n = mesh.n_cells
    t_end = t_now + dt

    t_new = t_old.copy()
    hot_surf = float(t_old[0])
    cold_surf = float(t_old[-1])
    q_hot = q_cold = 0.0
    residual = np.inf
    converged = False
    it = 0

    for it in range(1, opts.max_iterations + 1):
        h_hot = bc_hot.coefficient(hot_surf, t_end)
        h_cold = bc_cold.coefficient(cold_surf, t_end)
        env_hot = bc_hot.env_temperature(t_end)
        env_cold = bc_cold.env_temperature(t_end)

        k_cell = props.conductivity(t_new)
        cp_cell = props.specific_heat(0.5 * (t_old + t_new))
        cap = props.rho * cp_cell * mesh.volume / dt

        g = _face_conductances(mesh, k_cell, h_hot, h_cold)

        lower = np.zeros(n)
        upper = np.zeros(n)
        diag = cap + g[:-1] + g[1:]
        rhs = cap * t_old
        if n > 1:
            lower[1:] = -g[1:n]
            upper[:-1] = -g[1:n]
        rhs[0] += g[0] * env_hot
        rhs[-1] += g[n] * env_cold

        t_candidate = tdma(lower, diag, upper, rhs)
        if opts.relaxation < 1.0:
            t_candidate = t_new + opts.relaxation * (t_candidate - t_new)

        residual = float(np.max(np.abs(t_candidate - t_new)))
        t_new = t_candidate

        hot_surf, q_hot = _surface_temperature(env_hot, t_new[0], g[0], h_hot, mesh.face_area[0])
        cold_surf, q_cold = _surface_temperature(env_cold, t_new[-1], g[n], h_cold, mesh.face_area[-1])

        if residual < opts.tolerance:
            converged = True
            break

    return StepResult(
        T=t_new,
        hot_surface_K=hot_surf,
        cold_surface_K=cold_surf,
        q_hot=q_hot,
        q_cold=q_cold,
        iterations=it,
        converged=converged,
        residual=residual,
    )


def steady_state(
    mesh: Mesh,
    materials: list[Material],
    bc_hot: SurfaceBC,
    bc_cold: SurfaceBC,
    t_guess: np.ndarray | float = 800.0,
    max_iterations: int = 300,
    tolerance: float = 1.0e-6,
    relaxation: float = 0.7,
) -> np.ndarray:
    """Resuelve el estado estacionario no lineal (sin termino transitorio)."""
    props = _PropertyEvaluator(mesh, materials)
    n = mesh.n_cells
    t = np.full(n, float(t_guess)) if np.isscalar(t_guess) else np.asarray(t_guess, dtype=float).copy()
    hot_surf, cold_surf = float(t[0]), float(t[-1])

    for _ in range(max_iterations):
        h_hot = bc_hot.coefficient(hot_surf, 0.0)
        h_cold = bc_cold.coefficient(cold_surf, 0.0)
        env_hot = bc_hot.env_temperature(0.0)
        env_cold = bc_cold.env_temperature(0.0)

        g = _face_conductances(mesh, props.conductivity(t), h_hot, h_cold)
        lower = np.zeros(n)
        upper = np.zeros(n)
        diag = g[:-1] + g[1:]
        rhs = np.zeros(n)
        if n > 1:
            lower[1:] = -g[1:n]
            upper[:-1] = -g[1:n]
        rhs[0] += g[0] * env_hot
        rhs[-1] += g[n] * env_cold

        t_next = tdma(lower, diag, upper, rhs)
        t_next = t + relaxation * (t_next - t)
        delta = float(np.max(np.abs(t_next - t)))
        t = t_next
        hot_surf, _ = _surface_temperature(env_hot, t[0], g[0], h_hot, mesh.face_area[0])
        cold_surf, _ = _surface_temperature(env_cold, t[-1], g[n], h_cold, mesh.face_area[-1])
        if delta < tolerance:
            break
    return t


def internal_energy(mesh: Mesh, materials: list[Material], temp: np.ndarray, t_ref_k: float = 298.15) -> float:
    """Energia almacenada en la seccion respecto a `t_ref_k` [J]."""
    total = 0.0
    for i, material in enumerate(materials):
        mask = mesh.mat_index == i
        if not mask.any():
            continue
        for t_cell, vol in zip(temp[mask], mesh.volume[mask]):
            total += material.enthalpy_per_volume(t_cell, t_ref_k) * vol
    return float(total)
