"""Propiedades termofisicas de los materiales de la olla.

Las propiedades se definen como tablas lineales a trozos en funcion de la
temperatura (K). Fuera del rango tabulado se extrapola de forma plana
(se mantiene el valor del extremo), decision conservadora y explicita:
un modelo no debe inventar tendencias fuera de los datos disponibles.

Cada material lleva obligatoriamente un campo `source`. Un material sin
fuente documentada es un parametro libre disfrazado de dato.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import yaml

from .units import T0_K

DEFAULT_MATERIALS = Path(__file__).with_name("data") / "materials.yaml"

# Rango de integracion de entalpia. Fuera de el, cp se extrapola plana.
_H_TMIN, _H_TMAX = 200.0, 2200.0
_ENTHALPY_CACHE: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}


@dataclass(frozen=True)
class PropertyTable:
    """Propiedad lineal a trozos f(T). Temperaturas en K."""

    temperatures_k: np.ndarray
    values: np.ndarray
    name: str = ""

    def __post_init__(self) -> None:
        t = np.atleast_1d(np.asarray(self.temperatures_k, dtype=float))
        v = np.atleast_1d(np.asarray(self.values, dtype=float))
        if t.size != v.size:
            raise ValueError(f"{self.name}: {t.size} temperaturas vs {v.size} valores")
        if t.size == 0:
            raise ValueError(f"{self.name}: tabla vacia")
        if t.size > 1 and np.any(np.diff(t) <= 0):
            raise ValueError(f"{self.name}: temperaturas no crecientes")
        if np.any(v <= 0):
            raise ValueError(f"{self.name}: valores no positivos")
        object.__setattr__(self, "temperatures_k", t)
        object.__setattr__(self, "values", v)

    def __call__(self, t_k):
        return np.interp(t_k, self.temperatures_k, self.values)

    @property
    def is_constant(self) -> bool:
        return self.temperatures_k.size == 1 or bool(np.allclose(self.values, self.values[0]))

    @classmethod
    def from_spec(cls, spec, name: str = "") -> "PropertyTable":
        """Acepta un escalar, {'value': x} o {'temperatures_C': [...], 'values': [...]}."""
        if isinstance(spec, (int, float)):
            return cls(np.array([300.0]), np.array([float(spec)]), name)
        if not isinstance(spec, Mapping):
            raise TypeError(f"{name}: especificacion de propiedad no reconocida: {spec!r}")
        if "value" in spec:
            return cls(np.array([300.0]), np.array([float(spec["value"])]), name)
        if "temperatures_C" in spec:
            temps = np.asarray(spec["temperatures_C"], dtype=float) + T0_K
        elif "temperatures_K" in spec:
            temps = np.asarray(spec["temperatures_K"], dtype=float)
        else:
            raise KeyError(f"{name}: falta 'temperatures_C' / 'temperatures_K' / 'value'")
        return cls(temps, np.asarray(spec["values"], dtype=float), name)

    def mean_between(self, t1: float, t2: float) -> float:
        """Valor medio integral entre dos temperaturas (util para entalpias)."""
        if abs(t2 - t1) < 1e-12:
            return float(self(t1))
        grid = np.unique(np.concatenate(([min(t1, t2), max(t1, t2)], self.temperatures_k)))
        grid = grid[(grid >= min(t1, t2)) & (grid <= max(t1, t2))]
        return float(np.trapezoid(self(grid), grid) / (grid[-1] - grid[0]))


@dataclass(frozen=True)
class Material:
    """Material de una capa de la olla."""

    name: str
    density: float                    # [kg/m3]
    conductivity: PropertyTable       # k(T) [W/mK]
    specific_heat: PropertyTable      # cp(T) [J/kgK]
    emissivity: float = 0.85          # emisividad total hemisferica [-]
    max_service_C: float | None = None
    source: str = ""
    notes: str = ""

    def k(self, t_k):
        return self.conductivity(t_k)

    def cp(self, t_k):
        return self.specific_heat(t_k)

    def rho(self, t_k=None):
        return self.density

    def volumetric_heat_capacity(self, t_k):
        return self.density * self.cp(t_k)

    def diffusivity(self, t_k):
        """Difusividad termica alpha = k/(rho*cp) [m2/s]."""
        return self.k(t_k) / (self.density * self.cp(t_k))

    def enthalpy_per_volume(self, t_k, t_ref_k: float = 298.15):
        """Energia almacenada por unidad de volumen respecto a t_ref [J/m3].

        Integra rho*cp(T) de forma EXACTA. Como cp es lineal a trozos, su
        integral es cuadratica a trozos: interpolar linealmente la integral
        acumulada entre nodos introduce error (hasta ~0.2 % con las tablas de
        refractario de esta biblioteca). Por eso, dentro del tramo que contiene
        la temperatura consultada se aplica el trapecio sobre el subintervalo,
        que si es exacto para cp lineal. Vectorizado.
        """
        return self._integral(t_k) - self._integral(t_ref_k)

    def _integral(self, t_k):
        """Integral de rho*cp desde _H_TMIN hasta t_k [J/m3]."""
        grid_t, cumulative, rho_cp = self._enthalpy_grid()
        t = np.clip(np.asarray(t_k, dtype=float), _H_TMIN, _H_TMAX)
        idx = np.clip(np.searchsorted(grid_t, t, side="right") - 1, 0, grid_t.size - 2)
        rho_cp_at_t = self.density * self.specific_heat(t)
        return cumulative[idx] + 0.5 * (rho_cp[idx] + rho_cp_at_t) * (t - grid_t[idx])

    def _enthalpy_grid(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        cached = _ENTHALPY_CACHE.get(id(self))
        if cached is not None:
            return cached
        nodes = self.specific_heat.temperatures_k
        grid = np.unique(np.concatenate(([_H_TMIN], nodes, [_H_TMAX])))
        grid = grid[(grid >= _H_TMIN) & (grid <= _H_TMAX)]
        rho_cp = self.specific_heat(grid) * self.density
        cumulative = np.concatenate(([0.0], np.cumsum(0.5 * (rho_cp[1:] + rho_cp[:-1]) * np.diff(grid))))
        _ENTHALPY_CACHE[id(self)] = (grid, cumulative, rho_cp)
        return grid, cumulative, rho_cp

    @classmethod
    def from_spec(cls, name: str, spec: Mapping) -> "Material":
        missing = {"density", "conductivity", "specific_heat"} - set(spec)
        if missing:
            raise KeyError(f"material '{name}': faltan campos {sorted(missing)}")
        if not str(spec.get("source", "")).strip():
            raise ValueError(
                f"material '{name}': el campo 'source' es obligatorio. "
                "Un valor sin fuente es un parametro de ajuste, no un dato."
            )
        return cls(
            name=name,
            density=float(spec["density"]),
            conductivity=PropertyTable.from_spec(spec["conductivity"], f"{name}.k"),
            specific_heat=PropertyTable.from_spec(spec["specific_heat"], f"{name}.cp"),
            emissivity=float(spec.get("emissivity", 0.85)),
            max_service_C=(float(spec["max_service_C"]) if spec.get("max_service_C") is not None else None),
            source=str(spec["source"]).strip(),
            notes=str(spec.get("notes", "")).strip(),
        )


@dataclass(frozen=True)
class MaterialLibrary:
    """Coleccion de materiales indexada por nombre."""

    materials: dict[str, Material] = field(default_factory=dict)

    def __getitem__(self, name: str) -> Material:
        try:
            return self.materials[name]
        except KeyError:
            raise KeyError(
                f"material '{name}' no esta en la biblioteca. Disponibles: {sorted(self.materials)}"
            ) from None

    def __contains__(self, name: object) -> bool:
        return name in self.materials

    def __iter__(self):
        return iter(self.materials.values())

    def __len__(self) -> int:
        return len(self.materials)

    def names(self) -> list[str]:
        return sorted(self.materials)

    def subset(self, names: Iterable[str]) -> list[Material]:
        return [self[n] for n in names]


def load_materials(path: str | Path | None = None) -> MaterialLibrary:
    """Carga la biblioteca de materiales desde YAML."""
    path = Path(path) if path is not None else DEFAULT_MATERIALS
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    entries = raw.get("materials", raw)
    return MaterialLibrary({name: Material.from_spec(name, spec) for name, spec in entries.items()})
