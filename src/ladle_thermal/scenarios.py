"""Carga de estudios desde YAML y construccion de los objetos del modelo.

Un "estudio" es un archivo YAML que describe por completo una pregunta de
ingenieria: que olla, con que materiales, saliendo de que estado, enfriandose
de que maneras, con que precalentador y contra que criterio. El objetivo es
que reproducir o revisar un resultado sea leer un archivo, no leer codigo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml

from .boundary import (
    Adiabatic,
    AmbientShell,
    Convection,
    EmptyLadleCavity,
    FixedTemperature,
    LiquidSteelBath,
    PreheaterBurner,
    SurfaceBC,
)
from .cycle import Segment, uniform_state
from .geometry import Ladle, Section, load_ladle
from .materials import MaterialLibrary, load_materials
from .mesh import Mesh, build_mesh
from .preheat import ReadinessCriterion
from .solver import SolverOptions, steady_state
from .study import CoolingScenario, cyclic_steady_state


def _require(spec: Mapping, key: str, ctx: str) -> Any:
    if key not in spec:
        raise KeyError(f"{ctx}: falta la clave obligatoria '{key}'")
    return spec[key]


@dataclass
class StudyConfig:
    """Estudio cargado y listo para ejecutar."""

    name: str
    path: Path
    raw: dict
    ladle: Ladle
    library: MaterialLibrary
    section: Section
    mesh: Mesh
    material_names: tuple[str, ...]
    description: str = ""
    _materials: list = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------ base
    @property
    def materials(self) -> list:
        return self._materials

    @property
    def ambient(self) -> Mapping:
        return self.raw.get("ambient", {})

    @property
    def ambient_C(self) -> float:
        return float(self.ambient.get("temperature_C", 35.0))

    @property
    def cavity_depth(self) -> float:
        """Profundidad interior util para el intercambio radiativo por la boca."""
        explicit = self.raw.get("cavity_depth")
        if explicit is not None:
            return float(explicit)
        height = float(self.section.height or 3.0)
        return height + float(self.ladle.freeboard or 0.0)

    @property
    def cavity_area(self) -> float:
        """Area interior total que ve el quemador: pared lateral + fondo [m2]."""
        radius = float(self.section.inner_radius or 1.5)
        return 2.0 * math.pi * radius * self.cavity_depth + math.pi * radius ** 2

    # ------------------------------------------------- condiciones de frontera
    def shell_bc(self) -> AmbientShell:
        amb = self.ambient
        return AmbientShell(
            ambient_C=self.ambient_C,
            emissivity=float(amb.get("shell_emissivity", 0.80)),
            characteristic_length=float(amb.get("characteristic_length", self.section.height or 3.0)),
            orientation=str(amb.get("orientation", "vertical")),
            wind_speed=float(amb.get("wind_speed", 0.0)),
        )

    def build_bc(self, spec: Mapping | str, ctx: str = "bc") -> SurfaceBC:
        """Fabrica una condicion de frontera desde su especificacion YAML."""
        if isinstance(spec, str):
            spec = {"type": spec}
        kind = str(_require(spec, "type", ctx))

        if kind == "liquid_steel":
            return LiquidSteelBath(
                steel_temperature_C=float(spec.get("steel_C", 1600.0)),
                h=float(spec.get("h", 1500.0)),
                cooling_rate_C_per_min=float(spec.get("cooling_rate_C_per_min", 0.0)),
                name=str(spec.get("name", "acero_liquido")),
            )
        if kind in ("empty_open", "empty_lid", "empty"):
            lid = float(spec.get("lid_factor", 0.35 if kind == "empty_lid" else 1.0))
            return EmptyLadleCavity.from_section(
                inner_radius=float(self.section.inner_radius),
                inner_depth=float(spec.get("cavity_depth", self.cavity_depth)),
                ambient_C=float(spec.get("ambient_C", self.ambient_C)),
                emissivity=float(spec.get("emissivity", 0.85)),
                h_conv=float(spec.get("h_conv", 10.0)),
                lid_factor=lid,
            )
        if kind == "preheater":
            schedule = spec.get("schedule_C")
            power = spec.get("burner_power_MW")
            return PreheaterBurner(
                gas_temperature_C=float(spec.get("gas_temperature_C", 1250.0)),
                h_conv=float(spec.get("h_conv", 30.0)),
                eps_eff=float(spec.get("eps_eff", 0.70)),
                ramp_C_per_h=(float(spec["ramp_C_per_h"]) if spec.get("ramp_C_per_h") else None),
                start_temperature_C=(
                    float(spec["start_temperature_C"]) if spec.get("start_temperature_C") is not None else None
                ),
                schedule_C=(tuple((float(a), float(b)) for a, b in schedule) if schedule else None),
                burner_power_MW=(float(power) if power else None),
                adiabatic_flame_C=float(spec.get("adiabatic_flame_C", 1900.0)),
                heated_area=float(spec.get("heated_area", self.cavity_area)),
                ambient_C=float(spec.get("ambient_C", self.ambient_C)),
                name=str(spec.get("name", "precalentador")),
            )
        if kind == "convection":
            return Convection(h=float(spec.get("h", 10.0)), temperature_C=float(spec.get("temperature_C", 25.0)))
        if kind == "fixed_temperature":
            return FixedTemperature(temperature_C=float(_require(spec, "temperature_C", ctx)))
        if kind == "adiabatic":
            return Adiabatic()
        raise ValueError(
            f"{ctx}: tipo de condicion de frontera desconocido '{kind}'. "
            "Validos: liquid_steel, empty_open, empty_lid, preheater, convection, "
            "fixed_temperature, adiabatic."
        )

    # ---------------------------------------------------------------- piezas
    def options(self) -> SolverOptions:
        num = self.raw.get("numerics", {})
        return SolverOptions(
            dt=float(num.get("dt", 30.0)),
            dt_initial=float(num.get("dt_initial", 0.5)),
            dt_growth=float(num.get("dt_growth", 1.3)),
            max_iterations=int(num.get("max_iterations", 50)),
            tolerance=float(num.get("tolerance", 1.0e-4)),
            relaxation=float(num.get("relaxation", 1.0)),
        )

    def criterion(self) -> ReadinessCriterion:
        crit = self.raw.get("criterion", {})
        depth_mean = crit.get("depth_mean_C")
        return ReadinessCriterion(
            hot_face_C=float(crit.get("hot_face_C", 1100.0)),
            depth_mean_C=(float(depth_mean) if depth_mean is not None else None),
            depth_mm=float(crit.get("depth_mm", 25.0)),
        )

    def preheater(self) -> SurfaceBC:
        return self.build_bc(self.raw.get("preheater", {"type": "preheater"}), "preheater")

    def cooling_scenarios(self) -> list[CoolingScenario]:
        specs = self.raw.get("cooling_scenarios")
        if not specs:
            raise KeyError("el estudio no define 'cooling_scenarios'")
        out = []
        for spec in specs:
            name = str(_require(spec, "name", "cooling_scenarios"))
            bc = self.build_bc({k: v for k, v in spec.items() if k not in ("name", "description")},
                               f"cooling_scenarios/{name}")
            out.append(CoolingScenario(name=name, bc=bc, description=str(spec.get("description", ""))))
        return out

    def cooling_times_min(self) -> list[float]:
        times = self.raw.get("cooling_times_min", [0, 30, 60, 120, 180, 240])
        return [float(t) for t in times]

    def cycle_segments(self) -> list[Segment]:
        specs = self.raw.get("initial_state", {}).get("cycle", [])
        segments = []
        for spec in specs:
            name = str(_require(spec, "name", "initial_state/cycle"))
            minutes = float(_require(spec, "minutes", f"initial_state/cycle/{name}"))
            bc = self.build_bc({k: v for k, v in spec.items() if k not in ("name", "minutes")},
                               f"initial_state/cycle/{name}")
            segments.append(Segment(name=name, duration=minutes * 60.0, bc_hot=bc))
        return segments

    # -------------------------------------------------------- estado inicial
    def initial_state(self, verbose: bool = False) -> tuple[np.ndarray, str]:
        """Campo de temperaturas de partida y su descripcion trazable."""
        spec = self.raw.get("initial_state", {})
        mode = str(spec.get("mode", "cyclic"))
        opts = self.options()
        shell = self.shell_bc()

        if mode == "uniform":
            t_c = float(spec.get("uniform_C", 150.0))
            return uniform_state(self.mesh, t_c), f"campo uniforme a {t_c:.0f} C"

        if mode == "steady_with_steel":
            steel = self.build_bc(spec.get("steel", {"type": "liquid_steel"}), "initial_state/steel")
            state = steady_state(self.mesh, self.materials, steel, shell)
            return state, (
                "estacionario con acero dentro (limite superior: sobreestima el calor "
                f"almacenado; cara caliente {state[0]-273.15:.0f} C)"
            )

        if mode == "cyclic":
            segments = self.cycle_segments()
            if not segments:
                raise KeyError("initial_state/mode=cyclic requiere 'initial_state.cycle'")
            result = cyclic_steady_state(
                self.mesh, self.materials, segments, shell, opts,
                initial_C=float(spec.get("uniform_C", 150.0)),
                max_cycles=int(spec.get("max_cycles", 40)),
                tolerance_K=float(spec.get("tolerance_K", 1.0)),
            )
            if verbose:
                print("  " + result.summary(), flush=True)
            total_min = sum(s.duration for s in segments) / 60.0
            return result.state, (
                f"estado ciclico periodico tras {result.cycles} ciclos de {total_min:.0f} min "
                f"({'convergido' if result.converged else f'deriva {result.drift_K:.1f} K'})"
            )

        raise ValueError(
            f"initial_state.mode desconocido: '{mode}'. Validos: cyclic, steady_with_steel, uniform."
        )

    def describe(self) -> str:
        lines = [f"Estudio '{self.name}'  ({self.path})"]
        if self.description:
            lines.append(f"  {self.description}")
        lines.append(self.ladle.describe())
        lines.append(f"Seccion analizada: '{self.section.name}' ({self.mesh.n_cells} celdas)")
        lines.append(f"Ambiente: {self.ambient_C:.0f} C | profundidad de cavidad {self.cavity_depth:.2f} m")
        lines.append(f"Criterio: {self.criterion().describe()}")
        lines.append(f"Precalentador: {self.preheater().describe()}")
        lines.append("Escenarios de enfriamiento:")
        for sc in self.cooling_scenarios():
            lines.append(f"  - {sc.name}: {sc.describe()}")
        lines.append(f"Tiempos de espera [min]: {self.cooling_times_min()}")
        return "\n".join(lines)


def load_study(path: str | Path) -> StudyConfig:
    """Carga un estudio desde YAML resolviendo rutas relativas al propio archivo."""
    path = Path(path).resolve()
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    spec = raw.get("study", raw)

    base = path.parent
    ladle_path = _require(spec, "ladle", f"estudio {path.name}")
    ladle_path = Path(ladle_path)
    if not ladle_path.is_absolute():
        ladle_path = (base / ladle_path).resolve()
        if not ladle_path.exists():
            ladle_path = (Path.cwd() / spec["ladle"]).resolve()
    ladle = load_ladle(ladle_path)

    mat_path = spec.get("materials")
    if mat_path:
        mat_path = Path(mat_path)
        if not mat_path.is_absolute():
            candidate = (base / mat_path).resolve()
            mat_path = candidate if candidate.exists() else (Path.cwd() / spec["materials"]).resolve()
    library = load_materials(mat_path)

    section_name = str(spec.get("section", "wall"))
    section = ladle[section_name]
    names = tuple(library.names())
    mesh = build_mesh(section, names)

    config = StudyConfig(
        name=str(spec.get("name", path.stem)),
        path=path,
        raw=spec,
        ladle=ladle,
        library=library,
        section=section,
        mesh=mesh,
        material_names=names,
        description=str(spec.get("description", "")).strip(),
    )
    config._materials = [library[n] for n in names]
    return config
