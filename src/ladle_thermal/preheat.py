"""Determinacion del tiempo minimo de precalentamiento.

Pregunta que responde este modulo: dada una olla que sale de colada y se
enfria durante un tiempo en unas condiciones dadas, cuanto tiempo hay que
tenerla en el precalentador para que su revestimiento este en condiciones de
recibir acero otra vez.

Sobre el criterio "1100 C en la cara caliente": es necesario pero puede no ser
suficiente. Un precalentador agresivo puede poner la CARA a 1100 C en poco
tiempo dejando detras un refractario frio; al llenar, esa piel se enfria en
segundos contra la masa fria y el acero pierde temperatura igual. Por eso
`ReadinessCriterion` admite, ademas del criterio de cara, un criterio de
temperatura media hasta cierta profundidad, que es el que realmente controla
el calor que la olla le roba a la primera colada.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .boundary import SurfaceBC
from .cycle import History, Segment, concat_histories, run_segments
from .materials import Material
from .mesh import Mesh
from .solver import SolverOptions


@dataclass(frozen=True)
class ReadinessCriterion:
    """Criterio de "olla lista para recibir acero"."""

    hot_face_C: float = 1100.0
    depth_mean_C: float | None = None
    depth_mm: float = 25.0
    label: str = "listo para colada"

    def __post_init__(self) -> None:
        if self.depth_mm <= 0:
            raise ValueError("depth_mm debe ser > 0")

    def series(self, history: History) -> dict[str, np.ndarray]:
        """Series evaluadas sobre las que se aplica el criterio."""
        out = {"cara_caliente_C": history.hot_face_C}
        if self.depth_mean_C is not None:
            out[f"media_{self.depth_mm:.0f}mm_C"] = history.depth_mean_C(self.depth_mm / 1000.0)
        return out

    def targets(self) -> dict[str, float]:
        out = {"cara_caliente_C": self.hot_face_C}
        if self.depth_mean_C is not None:
            out[f"media_{self.depth_mm:.0f}mm_C"] = self.depth_mean_C
        return out

    def describe(self) -> str:
        parts = [f"cara caliente >= {self.hot_face_C:.0f} C"]
        if self.depth_mean_C is not None:
            parts.append(f"media de los primeros {self.depth_mm:.0f} mm >= {self.depth_mean_C:.0f} C")
        return " y ".join(parts)


@dataclass
class PreheatResult:
    """Resultado del calculo de tiempo de precalentamiento."""

    time_s: float | None
    criterion_met: bool
    limiting: str
    history: History
    criterion: ReadinessCriterion
    margin_C: dict[str, float] = field(default_factory=dict)

    @property
    def time_min(self) -> float | None:
        return None if self.time_s is None else self.time_s / 60.0

    @property
    def time_h(self) -> float | None:
        return None if self.time_s is None else self.time_s / 3600.0

    @property
    def hot_face_start_C(self) -> float:
        return float(self.history.hot_face_C[0])

    @property
    def hot_face_end_C(self) -> float:
        return float(self.history.hot_face_C[-1])

    def summary(self) -> str:
        if not self.criterion_met:
            worst = ", ".join(f"{k}={v:+.0f} K" for k, v in self.margin_C.items())
            return (
                f"NO se alcanza el criterio ({self.criterion.describe()}) en "
                f"{self.history.times[-1]/3600.0:.2f} h de precalentamiento.\n"
                f"  Margen al final de la simulacion: {worst}\n"
                f"  Criterio limitante: {self.limiting}"
            )
        return (
            f"Tiempo de precalentamiento requerido: {self.time_min:.0f} min "
            f"({self.time_h:.2f} h)\n"
            f"  Criterio: {self.criterion.describe()}\n"
            f"  Criterio limitante: {self.limiting}\n"
            f"  Cara caliente: {self.hot_face_start_C:.0f} C al inicio -> "
            f"{self.hot_face_end_C:.0f} C al final de la simulacion"
        )


def _first_sustained_index(mask: np.ndarray) -> int | None:
    """Primer indice a partir del cual `mask` es True hasta el final."""
    if not mask.any() or not mask[-1]:
        return None
    idx = mask.size - 1
    while idx > 0 and mask[idx - 1]:
        idx -= 1
    return idx


def _interpolate_crossing(times: np.ndarray, series: np.ndarray, target: float, idx: int) -> float:
    if idx == 0:
        return float(times[0])
    y0, y1 = float(series[idx - 1]), float(series[idx])
    if abs(y1 - y0) < 1e-12:
        return float(times[idx])
    frac = (target - y0) / (y1 - y0)
    frac = min(max(frac, 0.0), 1.0)
    return float(times[idx - 1] + frac * (times[idx] - times[idx - 1]))


def required_preheat_time(
    mesh: Mesh,
    materials: list[Material],
    initial_state: np.ndarray | float,
    burner: SurfaceBC,
    criterion: ReadinessCriterion | None = None,
    max_time: float = 24 * 3600.0,
    bc_cold: SurfaceBC | None = None,
    options: SolverOptions | None = None,
    segment_name: str = "precalentamiento",
    early_stop: bool = True,
    chunk: float = 3600.0,
) -> PreheatResult:
    """Simula el precalentamiento y localiza el instante en que se cumple el criterio.

    Se realiza UNA sola simulacion hasta `max_time` y se busca el cruce sobre la
    serie resultante. Es exacto y mucho mas barato que una biseccion, porque el
    calentamiento en el precalentador es monotono.
    """
    criterion = criterion or ReadinessCriterion()

    if not early_stop:
        history = run_segments(
            mesh=mesh, materials=materials,
            segments=[Segment(name=segment_name, duration=max_time, bc_hot=burner)],
            initial_state=initial_state, bc_cold=bc_cold, options=options,
        )
        return evaluate_readiness(history, criterion)

    # Simulacion por tramos con parada temprana. Bajo un quemador las series
    # del criterio crecen de forma monotona, asi que en cuanto se cumplen al
    # final de un tramo se cumplen definitivamente y no hace falta seguir
    # simulando hasta `max_time`.
    parts: list[History] = []
    state = initial_state
    elapsed = 0.0
    while elapsed < max_time - 1e-9:
        span = min(chunk, max_time - elapsed)
        part = run_segments(
            mesh=mesh, materials=materials,
            segments=[Segment(name=f"{segment_name}_{len(parts)}", duration=span, bc_hot=burner)],
            initial_state=state, bc_cold=bc_cold, options=options, t_start=elapsed,
        )
        parts.append(part)
        state = part.final_state
        elapsed += span
        if _criterion_satisfied_at_end(part, criterion):
            break

    merged = concat_histories(parts)
    merged.segment_names = (segment_name,)
    merged.segment_index = np.zeros_like(merged.segment_index)
    return evaluate_readiness(merged, criterion)


def _criterion_satisfied_at_end(history: History, criterion: ReadinessCriterion) -> bool:
    series = criterion.series(history)
    targets = criterion.targets()
    return all(float(series[name][-1]) >= targets[name] for name in series)


def evaluate_readiness(history: History, criterion: ReadinessCriterion) -> PreheatResult:
    """Aplica el criterio sobre un historial ya simulado."""
    series = criterion.series(history)
    targets = criterion.targets()

    masks = {name: series[name] >= targets[name] for name in series}
    combined = np.ones_like(history.times, dtype=bool)
    for mask in masks.values():
        combined &= mask

    idx = _first_sustained_index(combined)
    margins = {name: float(series[name][-1] - targets[name]) for name in series}

    if idx is None:
        limiting = min(margins, key=margins.get)
        return PreheatResult(
            time_s=None,
            criterion_met=False,
            limiting=limiting,
            history=history,
            criterion=criterion,
            margin_C=margins,
        )

    crossings = {}
    for name, mask in masks.items():
        if idx == 0 or mask[idx - 1]:
            crossings[name] = float(history.times[0]) if idx == 0 else float(history.times[idx - 1])
        else:
            crossings[name] = _interpolate_crossing(history.times, series[name], targets[name], idx)
    limiting = max(crossings, key=crossings.get)

    return PreheatResult(
        time_s=crossings[limiting],
        criterion_met=True,
        limiting=limiting,
        history=history,
        criterion=criterion,
        margin_C=margins,
    )
