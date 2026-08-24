"""Geometria de la olla: pila de capas y secciones 1D.

Convencion de orden: las capas se declaran SIEMPRE desde la cara caliente
(en contacto con el acero) hacia la cara fria (carcasa / ambiente). El indice
0 del malla es siempre la cara caliente.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Mapping, Sequence

import yaml

Geometry = Literal["cylindrical", "planar"]


@dataclass(frozen=True)
class Layer:
    """Una capa del revestimiento."""

    name: str
    material: str
    thickness: float                 # [m]
    n_cells: int = 10
    grading: float = 1.0             # >1 refina hacia la cara caliente de la capa
    contact_resistance: float = 0.0  # [m2K/W] en la interfaz del lado FRIO de esta capa

    def __post_init__(self) -> None:
        if self.thickness <= 0:
            raise ValueError(f"capa '{self.name}': espesor debe ser > 0 (recibido {self.thickness})")
        if self.n_cells < 1:
            raise ValueError(f"capa '{self.name}': n_cells debe ser >= 1")
        if self.grading <= 0:
            raise ValueError(f"capa '{self.name}': grading debe ser > 0")
        if self.contact_resistance < 0:
            raise ValueError(f"capa '{self.name}': contact_resistance no puede ser negativa")

    @classmethod
    def from_spec(cls, spec: Mapping) -> "Layer":
        thickness = spec.get("thickness_mm")
        if thickness is not None:
            thickness = float(thickness) / 1000.0
        else:
            thickness = float(spec["thickness"])
        return cls(
            name=str(spec["name"]),
            material=str(spec["material"]),
            thickness=thickness,
            n_cells=int(spec.get("n_cells", 10)),
            grading=float(spec.get("grading", 1.0)),
            contact_resistance=float(spec.get("contact_resistance", 0.0)),
        )


@dataclass(frozen=True)
class Section:
    """Una pila 1D de capas con su geometria (pared cilindrica o fondo plano)."""

    name: str
    layers: tuple[Layer, ...]
    geometry: Geometry = "cylindrical"
    inner_radius: float | None = None   # [m] requerido si cylindrical
    height: float | None = None         # [m] altura util, requerido si cylindrical
    area: float | None = None           # [m2] requerido si planar

    def __post_init__(self) -> None:
        if not self.layers:
            raise ValueError(f"seccion '{self.name}': sin capas")
        if self.geometry == "cylindrical":
            if not self.inner_radius or self.inner_radius <= 0:
                raise ValueError(f"seccion '{self.name}': cylindrical requiere inner_radius > 0")
            if not self.height or self.height <= 0:
                raise ValueError(f"seccion '{self.name}': cylindrical requiere height > 0")
        elif self.geometry == "planar":
            if not self.area or self.area <= 0:
                raise ValueError(f"seccion '{self.name}': planar requiere area > 0")
        else:
            raise ValueError(f"seccion '{self.name}': geometry desconocida '{self.geometry}'")

    @property
    def total_thickness(self) -> float:
        return sum(layer.thickness for layer in self.layers)

    @property
    def n_cells(self) -> int:
        return sum(layer.n_cells for layer in self.layers)

    @property
    def outer_radius(self) -> float | None:
        if self.geometry != "cylindrical":
            return None
        return self.inner_radius + self.total_thickness

    @property
    def hot_area(self) -> float:
        """Area de la cara caliente [m2]."""
        if self.geometry == "cylindrical":
            return 2.0 * math.pi * self.inner_radius * self.height
        return self.area

    @property
    def cold_area(self) -> float:
        """Area de la cara fria [m2]."""
        if self.geometry == "cylindrical":
            return 2.0 * math.pi * self.outer_radius * self.height
        return self.area

    def layer_named(self, name: str) -> Layer:
        for layer in self.layers:
            if layer.name == name:
                return layer
        raise KeyError(f"seccion '{self.name}': no existe la capa '{name}'")

    def describe(self) -> str:
        rows = [f"Seccion '{self.name}' ({self.geometry}), espesor total {self.total_thickness*1000:.0f} mm"]
        if self.geometry == "cylindrical":
            rows.append(
                f"  r_int = {self.inner_radius:.3f} m, r_ext = {self.outer_radius:.3f} m, "
                f"altura = {self.height:.3f} m"
            )
        else:
            rows.append(f"  area = {self.area:.3f} m2")
        rows.append(f"  A_caliente = {self.hot_area:.2f} m2, A_fria = {self.cold_area:.2f} m2")
        for i, layer in enumerate(self.layers):
            rows.append(
                f"  [{i}] {layer.name:<22s} {layer.material:<28s} "
                f"{layer.thickness*1000:6.1f} mm  {layer.n_cells:3d} celdas"
                + (f"  Rc={layer.contact_resistance:.4f} m2K/W" if layer.contact_resistance else "")
            )
        return "\n".join(rows)

    @classmethod
    def from_spec(cls, name: str, spec: Mapping) -> "Section":
        inner_radius = spec.get("inner_radius")
        if inner_radius is None and spec.get("inner_diameter") is not None:
            inner_radius = float(spec["inner_diameter"]) / 2.0
        return cls(
            name=name,
            layers=tuple(Layer.from_spec(s) for s in spec["layers"]),
            geometry=str(spec.get("geometry", "cylindrical")),
            inner_radius=(float(inner_radius) if inner_radius is not None else None),
            height=(float(spec["height"]) if spec.get("height") is not None else None),
            area=(float(spec["area"]) if spec.get("area") is not None else None),
        )


@dataclass(frozen=True)
class Ladle:
    """Olla completa: una o mas secciones 1D independientes."""

    name: str
    sections: dict[str, Section] = field(default_factory=dict)
    capacity_t: float | None = None
    freeboard: float | None = None
    notes: str = ""

    def __getitem__(self, name: str) -> Section:
        try:
            return self.sections[name]
        except KeyError:
            raise KeyError(
                f"olla '{self.name}': no existe la seccion '{name}'. Disponibles: {sorted(self.sections)}"
            ) from None

    @property
    def wall(self) -> Section:
        return self["wall"]

    @property
    def bottom(self) -> Section | None:
        return self.sections.get("bottom")

    @property
    def inner_diameter(self) -> float | None:
        wall = self.sections.get("wall")
        return 2.0 * wall.inner_radius if wall and wall.inner_radius else None

    def describe(self) -> str:
        head = [f"Olla '{self.name}'" + (f" - capacidad {self.capacity_t:.0f} t" if self.capacity_t else "")]
        if self.notes:
            head.append(f"  {self.notes}")
        return "\n".join(head + [sec.describe() for sec in self.sections.values()])


def load_ladle(path: str | Path) -> Ladle:
    """Carga la definicion geometrica de una olla desde YAML."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    spec = raw.get("ladle", raw)
    sections = {name: Section.from_spec(name, s) for name, s in spec["sections"].items()}
    return Ladle(
        name=str(spec.get("name", Path(path).stem)),
        sections=sections,
        capacity_t=(float(spec["capacity_t"]) if spec.get("capacity_t") is not None else None),
        freeboard=(float(spec["freeboard"]) if spec.get("freeboard") is not None else None),
        notes=str(spec.get("notes", "")).strip(),
    )
