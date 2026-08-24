"""Estudios parametricos: del escenario de enfriamiento al tiempo de precalentador.

Este modulo produce el entregable central del proyecto: una tabla que, para
cada escenario de enfriamiento sin aporte energetico (olla vacia esperando, con
o sin tapa, mas o menos tiempo), dice cuanto precalentador hace falta para
devolver el revestimiento a condiciones de colada.

Estrategia de calculo: para cada escenario se simula UNA sola curva de
enfriamiento hasta el tiempo maximo y se extraen de ella los estados
intermedios. Solo el precalentamiento se re-simula para cada punto. Esto
reduce el coste del mapa de O(n^2) a O(n).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .boundary import AmbientShell, SurfaceBC
from .cycle import History, Segment, run_segments, uniform_state
from .materials import Material
from .mesh import Mesh
from .preheat import PreheatResult, ReadinessCriterion, evaluate_readiness, required_preheat_time
from .solver import SolverOptions
from .units import T0_K


@dataclass
class CoolingScenario:
    """Un modo de enfriamiento sin aporte energetico."""

    name: str
    bc: SurfaceBC
    description: str = ""

    def describe(self) -> str:
        return self.description or self.bc.describe()


@dataclass
class CyclicStateResult:
    """Estado termico periodico de una olla en rotacion."""

    state: np.ndarray
    cycles: int
    converged: bool
    drift_K: float
    last_history: History

    @property
    def hot_face_C(self) -> float:
        return float(self.state[0] - T0_K)

    def summary(self) -> str:
        status = "convergido" if self.converged else f"NO convergido (deriva {self.drift_K:.2f} K)"
        return (
            f"Estado ciclico periodico tras {self.cycles} ciclos ({status}). "
            f"Inicio de ciclo: cara caliente {self.hot_face_C:.0f} C, "
            f"carcasa {self.state[-1]-T0_K:.0f} C"
        )


def cyclic_steady_state(
    mesh: Mesh,
    materials: list[Material],
    segments: list[Segment],
    bc_cold: SurfaceBC | None = None,
    options: SolverOptions | None = None,
    initial_C: float = 150.0,
    max_cycles: int = 40,
    tolerance_K: float = 1.0,
) -> CyclicStateResult:
    """Repite el ciclo hasta que el campo de temperaturas se vuelve periodico.

    Una olla en produccion no arranca fria ni desde el estacionario con acero:
    arranca desde el estado que le deja el ciclo anterior. Ese es el punto de
    partida correcto para dimensionar el precalentador, y usar cualquier otro
    sesga el resultado (frio -> sobreestima; estacionario -> subestima).
    """
    state = uniform_state(mesh, initial_C)
    history = None
    drift = math.inf
    cycle = 0
    for cycle in range(1, max_cycles + 1):
        history = run_segments(mesh, materials, segments, state, bc_cold, options)
        new_state = history.final_state
        drift = float(np.max(np.abs(new_state - state)))
        state = new_state
        if drift < tolerance_K:
            break
    return CyclicStateResult(
        state=state,
        cycles=cycle,
        converged=drift < tolerance_K,
        drift_K=drift,
        last_history=history,
    )


@dataclass
class MapEntry:
    """Una celda del mapa enfriamiento -> precalentamiento."""

    scenario: str
    cooling_min: float
    hot_face_after_cooling_C: float
    depth_mean_after_cooling_C: float
    shell_after_cooling_C: float
    preheat_min: float | None
    limiting: str
    criterion_met: bool
    energy_deficit_MJ: float


@dataclass
class PreheatMap:
    """Resultado completo del estudio."""

    entries: list[MapEntry]
    scenarios: list[CoolingScenario]
    cooling_times_min: list[float]
    criterion: ReadinessCriterion
    burner_description: str
    cooling_histories: dict[str, History] = field(default_factory=dict)
    preheat_histories: dict[tuple[str, float], History] = field(default_factory=dict)
    initial_state_description: str = ""

    def entry(self, scenario: str, cooling_min: float) -> MapEntry:
        for e in self.entries:
            if e.scenario == scenario and abs(e.cooling_min - cooling_min) < 1e-6:
                return e
        raise KeyError(f"no hay entrada para ({scenario}, {cooling_min} min)")

    def matrix(self) -> np.ndarray:
        """Matriz [escenario x tiempo_enfriamiento] de minutos de precalentador (NaN si no se alcanza)."""
        out = np.full((len(self.scenarios), len(self.cooling_times_min)), np.nan)
        for i, sc in enumerate(self.scenarios):
            for j, ct in enumerate(self.cooling_times_min):
                e = self.entry(sc.name, ct)
                out[i, j] = np.nan if e.preheat_min is None else e.preheat_min
        return out

    def to_markdown(self) -> str:
        header = "| Escenario | Espera vacia [min] | Cara caliente tras espera [C] | Media 25 mm [C] | Carcasa [C] | Precalentador requerido [min] | Criterio limitante |"
        sep = "|---|---:|---:|---:|---:|---:|---|"
        rows = [header, sep]
        for e in self.entries:
            pre = "no alcanzado" if e.preheat_min is None else f"{e.preheat_min:.0f}"
            rows.append(
                f"| {e.scenario} | {e.cooling_min:.0f} | {e.hot_face_after_cooling_C:.0f} | "
                f"{e.depth_mean_after_cooling_C:.0f} | {e.shell_after_cooling_C:.0f} | {pre} | {e.limiting} |"
            )
        return "\n".join(rows)

    def to_csv_rows(self) -> list[list[str]]:
        rows = [[
            "escenario", "espera_vacia_min", "cara_caliente_tras_espera_C",
            "media_25mm_tras_espera_C", "carcasa_C", "precalentador_min",
            "criterio_limitante", "criterio_alcanzado", "deficit_energia_MJ",
        ]]
        for e in self.entries:
            rows.append([
                e.scenario, f"{e.cooling_min:.1f}", f"{e.hot_face_after_cooling_C:.1f}",
                f"{e.depth_mean_after_cooling_C:.1f}", f"{e.shell_after_cooling_C:.1f}",
                "" if e.preheat_min is None else f"{e.preheat_min:.1f}",
                e.limiting, "si" if e.criterion_met else "no", f"{e.energy_deficit_MJ:.1f}",
            ])
        return rows


def build_preheat_map(
    mesh: Mesh,
    materials: list[Material],
    initial_state: np.ndarray,
    scenarios: list[CoolingScenario],
    cooling_times_min: list[float],
    burner: SurfaceBC,
    criterion: ReadinessCriterion | None = None,
    bc_cold: SurfaceBC | None = None,
    options: SolverOptions | None = None,
    max_preheat_h: float = 24.0,
    keep_histories: bool = True,
    progress: bool = False,
) -> PreheatMap:
    """Construye el mapa escenario x tiempo de espera -> minutos de precalentador."""
    criterion = criterion or ReadinessCriterion()
    bc_cold = bc_cold or AmbientShell()
    cooling_times_min = sorted(float(t) for t in cooling_times_min)
    max_cooling_s = max(cooling_times_min) * 60.0
    depth_m = criterion.depth_mm / 1000.0

    from .solver import internal_energy

    entries: list[MapEntry] = []
    cooling_histories: dict[str, History] = {}
    preheat_histories: dict[tuple[str, float], History] = {}

    # Energia de referencia: la que tendria la olla justo al cumplir el criterio
    # de forma "plana" (aproximacion: perfil del estado inicial). Se usa solo
    # como indicador relativo de cuanto calor hay que devolverle.
    reference_energy = internal_energy(mesh, materials, initial_state)

    for scenario in scenarios:
        cooling = run_segments(
            mesh, materials,
            [Segment(f"enfriamiento_{scenario.name}", max_cooling_s, scenario.bc)],
            initial_state, bc_cold, options,
        )
        if keep_histories:
            cooling_histories[scenario.name] = cooling

        for ct in cooling_times_min:
            state = cooling.state_at(ct * 60.0)
            result: PreheatResult = required_preheat_time(
                mesh, materials, state, burner, criterion,
                max_time=max_preheat_h * 3600.0, bc_cold=bc_cold, options=options,
            )
            mask = mesh.cells_within_depth(depth_m)
            w = mesh.volume[mask]
            mean_depth_C = float((state[mask] @ w) / w.sum() - T0_K)
            deficit = (reference_energy - internal_energy(mesh, materials, state)) / 1e6

            entries.append(MapEntry(
                scenario=scenario.name,
                cooling_min=ct,
                hot_face_after_cooling_C=float(np.interp(ct * 60.0, cooling.times, cooling.hot_face_C)),
                depth_mean_after_cooling_C=mean_depth_C,
                shell_after_cooling_C=float(np.interp(ct * 60.0, cooling.times, cooling.shell_C)),
                preheat_min=result.time_min,
                limiting=result.limiting,
                criterion_met=result.criterion_met,
                energy_deficit_MJ=deficit,
            ))
            if keep_histories:
                preheat_histories[(scenario.name, ct)] = result.history
            if progress:
                pre = "n/a" if result.time_min is None else f"{result.time_min:6.1f} min"
                print(f"  [{scenario.name:<24s}] espera {ct:6.0f} min -> precalentador {pre}", flush=True)

    return PreheatMap(
        entries=entries,
        scenarios=scenarios,
        cooling_times_min=cooling_times_min,
        criterion=criterion,
        burner_description=burner.describe(),
        cooling_histories=cooling_histories,
        preheat_histories=preheat_histories,
    )
