"""Orquestacion de ciclos termicos: segmentos, integracion e historial.

Un ciclo de olla es una secuencia de segmentos con distinta condicion de
frontera en la cara caliente: llenado con acero, retencion, colada, espera
vacia, tapada, precalentamiento. El campo de temperaturas se arrastra de un
segmento al siguiente: esa continuidad es justamente lo que hace que el
tiempo de precalentamiento dependa de la historia previa de la olla.

El tiempo que ven las condiciones de frontera es LOCAL al segmento (empieza
en 0 en cada segmento), de modo que rampas y programas se definen de forma
natural. El historial guarda el tiempo global.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .boundary import AmbientShell, SurfaceBC
from .materials import Material
from .mesh import Mesh
from .solver import SolverOptions, StepResult, _PropertyEvaluator, internal_energy, step
from .units import T0_K


@dataclass
class Segment:
    """Un tramo del ciclo con condiciones de frontera constantes en forma."""

    name: str
    duration: float                       # [s]
    bc_hot: SurfaceBC
    bc_cold: SurfaceBC | None = None      # None => se usa la del ciclo
    options: SolverOptions | None = None

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError(f"segmento '{self.name}': duracion debe ser > 0")

    @property
    def duration_min(self) -> float:
        return self.duration / 60.0


@dataclass
class History:
    """Series temporales de una corrida."""

    mesh: Mesh
    materials: list[Material]
    times: np.ndarray                 # [s] tiempo global
    temperatures: np.ndarray          # [n_samples, n_cells] en K
    hot_surface_K: np.ndarray
    cold_surface_K: np.ndarray
    q_hot: np.ndarray                 # [W]
    q_cold: np.ndarray                # [W]
    segment_index: np.ndarray
    segment_names: tuple[str, ...]
    non_converged_steps: int = 0
    metadata: dict = field(default_factory=dict)

    # --- vistas convenientes en Celsius --------------------------------------
    @property
    def times_min(self) -> np.ndarray:
        return self.times / 60.0

    @property
    def times_h(self) -> np.ndarray:
        return self.times / 3600.0

    @property
    def hot_face_C(self) -> np.ndarray:
        """Temperatura de la CARA caliente del refractario [C]."""
        return self.hot_surface_K - T0_K

    @property
    def shell_C(self) -> np.ndarray:
        """Temperatura de la cara externa de la carcasa [C]."""
        return self.cold_surface_K - T0_K

    @property
    def final_state(self) -> np.ndarray:
        return self.temperatures[-1].copy()

    @property
    def initial_state(self) -> np.ndarray:
        return self.temperatures[0].copy()

    def state_at(self, t: float) -> np.ndarray:
        """Campo de temperaturas [K] interpolado linealmente en el tiempo global t [s]."""
        if t <= self.times[0]:
            return self.temperatures[0].copy()
        if t >= self.times[-1]:
            return self.temperatures[-1].copy()
        idx = int(np.searchsorted(self.times, t))
        t0, t1 = self.times[idx - 1], self.times[idx]
        w = (t - t0) / (t1 - t0)
        return (1.0 - w) * self.temperatures[idx - 1] + w * self.temperatures[idx]

    def profile_C(self, index: int = -1) -> np.ndarray:
        return self.temperatures[index] - T0_K

    def depth_mean_C(self, depth_m: float) -> np.ndarray:
        """Media (ponderada por volumen) hasta `depth_m` de la cara caliente [C]."""
        mask = self.mesh.cells_within_depth(depth_m)
        if not mask.any():
            mask = np.zeros(self.mesh.n_cells, dtype=bool)
            mask[0] = True
        w = self.mesh.volume[mask]
        return (self.temperatures[:, mask] @ w) / w.sum() - T0_K

    def layer_mean_C(self, layer_name: str) -> np.ndarray:
        mask = self.mesh.layer_mask(layer_name)
        w = self.mesh.volume[mask]
        return (self.temperatures[:, mask] @ w) / w.sum() - T0_K

    def stored_energy_J(self) -> np.ndarray:
        """Energia almacenada en la seccion respecto a 25 C [J], por muestra."""
        out = np.empty(self.times.size)
        for i in range(self.times.size):
            out[i] = internal_energy(self.mesh, self.materials, self.temperatures[i])
        return out

    def time_of_first_crossing(self, series: np.ndarray, target: float, rising: bool = True) -> float | None:
        """Instante [s] en que `series` cruza `target`, con interpolacion lineal."""
        cond = series >= target if rising else series <= target
        idx = np.argmax(cond) if cond.any() else None
        if idx is None:
            return None
        if idx == 0:
            return float(self.times[0])
        y0, y1 = series[idx - 1], series[idx]
        if abs(y1 - y0) < 1e-12:
            return float(self.times[idx])
        frac = (target - y0) / (y1 - y0)
        return float(self.times[idx - 1] + frac * (self.times[idx] - self.times[idx - 1]))

    def segment_bounds(self, name: str) -> tuple[float, float]:
        idx = self.segment_names.index(name)
        mask = self.segment_index == idx
        return float(self.times[mask][0]), float(self.times[mask][-1])

    def to_csv(self, path: str | Path, include_profile: bool = False) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        header = ["t_s", "t_min", "segmento", "cara_caliente_C", "carcasa_C", "q_cara_caliente_W", "q_carcasa_W"]
        if include_profile:
            header += [f"T_{d*1000:.0f}mm_C" for d in self.mesh.depth_node]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            for i in range(self.times.size):
                row = [
                    f"{self.times[i]:.2f}",
                    f"{self.times[i]/60.0:.4f}",
                    self.segment_names[self.segment_index[i]],
                    f"{self.hot_face_C[i]:.3f}",
                    f"{self.shell_C[i]:.3f}",
                    f"{self.q_hot[i]:.1f}",
                    f"{self.q_cold[i]:.1f}",
                ]
                if include_profile:
                    row += [f"{v:.3f}" for v in self.profile_C(i)]
                writer.writerow(row)
        return path

    def summary(self) -> str:
        lines = [
            f"Corrida sobre seccion '{self.mesh.section_name}' "
            f"({self.mesh.n_cells} celdas, {self.times.size} muestras)",
            f"  duracion total: {self.times[-1]/3600.0:.2f} h",
            f"  cara caliente: {self.hot_face_C[0]:.0f} C -> {self.hot_face_C[-1]:.0f} C",
            f"  carcasa:       {self.shell_C[0]:.0f} C -> {self.shell_C[-1]:.0f} C",
        ]
        for i, name in enumerate(self.segment_names):
            mask = self.segment_index == i
            if not mask.any():
                continue
            lines.append(
                f"  [{name}] {self.times[mask][0]/60.0:7.1f} -> {self.times[mask][-1]/60.0:7.1f} min | "
                f"cara caliente {self.hot_face_C[mask][0]:6.0f} -> {self.hot_face_C[mask][-1]:6.0f} C"
            )
        if self.non_converged_steps:
            lines.append(f"  AVISO: {self.non_converged_steps} pasos no convergieron")
        return "\n".join(lines)


def concat_histories(parts: list[History]) -> History:
    """Une historiales consecutivos descartando la muestra duplicada del empalme."""
    if len(parts) == 1:
        return parts[0]
    first = parts[0]
    seg_names: list[str] = list(first.segment_names)
    chunks = {k: [getattr(first, k)] for k in
              ("times", "temperatures", "hot_surface_K", "cold_surface_K", "q_hot", "q_cold")}
    seg_idx = [first.segment_index]
    for part in parts[1:]:
        offset = len(seg_names)
        seg_names.extend(part.segment_names)
        for key in chunks:
            chunks[key].append(getattr(part, key)[1:])
        seg_idx.append(part.segment_index[1:] + offset)
    return History(
        mesh=first.mesh,
        materials=first.materials,
        times=np.concatenate(chunks["times"]),
        temperatures=np.concatenate(chunks["temperatures"]),
        hot_surface_K=np.concatenate(chunks["hot_surface_K"]),
        cold_surface_K=np.concatenate(chunks["cold_surface_K"]),
        q_hot=np.concatenate(chunks["q_hot"]),
        q_cold=np.concatenate(chunks["q_cold"]),
        segment_index=np.concatenate(seg_idx),
        segment_names=tuple(seg_names),
        non_converged_steps=sum(p.non_converged_steps for p in parts),
        metadata=dict(first.metadata),
    )


def uniform_state(mesh: Mesh, temperature_C: float) -> np.ndarray:
    """Campo inicial uniforme."""
    return np.full(mesh.n_cells, temperature_C + T0_K)


def run_segments(
    mesh: Mesh,
    materials: list[Material],
    segments: list[Segment],
    initial_state: np.ndarray | float,
    bc_cold: SurfaceBC | None = None,
    options: SolverOptions | None = None,
    t_start: float = 0.0,
) -> History:
    """Integra una secuencia de segmentos arrastrando el campo de temperaturas."""
    if not segments:
        raise ValueError("se requiere al menos un segmento")
    base_opts = options or SolverOptions()
    default_cold = bc_cold or AmbientShell()
    props = _PropertyEvaluator(mesh, materials)

    temp = (
        uniform_state(mesh, float(initial_state))
        if np.isscalar(initial_state)
        else np.asarray(initial_state, dtype=float).copy()
    )
    if temp.size != mesh.n_cells:
        raise ValueError(f"estado inicial de tamano {temp.size}, la malla tiene {mesh.n_cells} celdas")

    times = [t_start]
    fields = [temp.copy()]
    hot_s = [float(temp[0])]
    cold_s = [float(temp[-1])]
    q_hot = [0.0]
    q_cold = [0.0]
    seg_idx = [0]
    non_converged = 0

    t_global = t_start
    for si, segment in enumerate(segments):
        opts = segment.options or base_opts
        cold = segment.bc_cold or default_cold
        # Estado inicial del segmento: relanza la evaluacion de las fronteras
        h_hot0 = segment.bc_hot.coefficient(float(temp[0]), 0.0)
        if si == 0:
            hot_s[0], cold_s[0] = float(temp[0]), float(temp[-1])
        t_local = 0.0
        dt = opts.dt_initial if opts.dt_initial else opts.dt
        while t_local < segment.duration - 1e-9:
            dt_use = min(dt, segment.duration - t_local)
            result: StepResult = step(
                mesh, materials, temp, dt_use, segment.bc_hot, cold, t_local, opts, props
            )
            if not result.converged:
                non_converged += 1
            temp = result.T
            t_local += dt_use
            t_global += dt_use
            times.append(t_global)
            fields.append(temp.copy())
            hot_s.append(result.hot_surface_K)
            cold_s.append(result.cold_surface_K)
            q_hot.append(result.q_hot)
            q_cold.append(result.q_cold)
            seg_idx.append(si)
            dt = min(dt * opts.dt_growth, opts.dt)

    return History(
        mesh=mesh,
        materials=materials,
        times=np.asarray(times),
        temperatures=np.asarray(fields),
        hot_surface_K=np.asarray(hot_s),
        cold_surface_K=np.asarray(cold_s),
        q_hot=np.asarray(q_hot),
        q_cold=np.asarray(q_cold),
        segment_index=np.asarray(seg_idx, dtype=int),
        segment_names=tuple(s.name for s in segments),
        non_converged_steps=non_converged,
        metadata={"h_hot_inicial": h_hot0},
    )
