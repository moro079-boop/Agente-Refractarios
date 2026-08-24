"""Discretizacion por volumenes finitos de una seccion 1D.

Se genera una malla de celdas contiguas desde la cara caliente (indice 0)
hasta la cara fria. Para cada celda se precalculan factores geometricos de
resistencia `g` tales que la resistencia termica de media celda vale R = g/k
[K/W]. Esto unifica el tratamiento cilindrico y plano: solo cambia `g`.

  - Cilindrico (pared):  g = ln(r_2/r_1) / (2*pi*H)
  - Plano (fondo):       g = (x_2 - x_1) / A
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .geometry import Section


def _cell_widths(thickness: float, n_cells: int, grading: float) -> np.ndarray:
    """Anchos de celda. grading > 1 => celdas mas finas en la cara caliente."""
    if n_cells == 1:
        return np.array([thickness])
    if abs(grading - 1.0) < 1e-12:
        return np.full(n_cells, thickness / n_cells)
    weights = grading ** np.arange(n_cells, dtype=float)
    return thickness * weights / weights.sum()


@dataclass(frozen=True)
class Mesh:
    """Malla 1D de volumenes finitos.

    Atributos (n = numero de celdas):
      x_face      (n+1,) coordenada de las caras: radio [m] si cilindrico,
                         profundidad desde la cara caliente [m] si plano
      x_node      (n,)   coordenada del centro de celda
      depth_node  (n,)   profundidad desde la cara caliente [m] (siempre)
      volume      (n,)   volumen de celda [m3]
      face_area   (n+1,) area de cada cara [m2]
      g_minus     (n,)   factor geometrico nodo -> cara caliente de su celda
      g_plus      (n,)   factor geometrico nodo -> cara fria de su celda
      contact_R   (n+1,) resistencia de contacto en cada cara [K/W]
      mat_index   (n,)   indice del material de cada celda
      layer_index (n,)   indice de la capa de cada celda
    """

    section_name: str
    geometry: str
    x_face: np.ndarray
    x_node: np.ndarray
    depth_node: np.ndarray
    volume: np.ndarray
    face_area: np.ndarray
    g_minus: np.ndarray
    g_plus: np.ndarray
    contact_R: np.ndarray
    mat_index: np.ndarray
    layer_index: np.ndarray
    material_names: tuple[str, ...]
    layer_names: tuple[str, ...]

    @property
    def n_cells(self) -> int:
        return self.volume.size

    @property
    def hot_area(self) -> float:
        return float(self.face_area[0])

    @property
    def cold_area(self) -> float:
        return float(self.face_area[-1])

    @property
    def total_volume(self) -> float:
        return float(self.volume.sum())

    def cells_within_depth(self, depth_m: float) -> np.ndarray:
        """Mascara booleana de celdas cuyo centro esta dentro de `depth_m` de la cara caliente."""
        return self.depth_node <= depth_m

    def layer_mask(self, layer_name: str) -> np.ndarray:
        try:
            idx = self.layer_names.index(layer_name)
        except ValueError:
            raise KeyError(
                f"malla '{self.section_name}': no existe la capa '{layer_name}'. "
                f"Disponibles: {list(self.layer_names)}"
            ) from None
        return self.layer_index == idx

    def depth_average(self, values: np.ndarray, depth_m: float) -> float:
        """Media ponderada por volumen de `values` sobre las celdas hasta `depth_m`."""
        mask = self.cells_within_depth(depth_m)
        if not mask.any():
            mask = np.zeros(self.n_cells, dtype=bool)
            mask[0] = True
        w = self.volume[mask]
        return float(np.sum(values[mask] * w) / w.sum())


def build_mesh(section: Section, material_names: tuple[str, ...] | list[str]) -> Mesh:
    """Construye la malla de una seccion. `material_names` fija el orden de indices."""
    material_names = tuple(material_names)
    widths: list[np.ndarray] = []
    mat_index: list[int] = []
    layer_index: list[int] = []
    interface_r: list[float] = []   # resistencia de contacto [m2K/W] por cara

    for li, layer in enumerate(section.layers):
        if layer.material not in material_names:
            raise KeyError(
                f"seccion '{section.name}', capa '{layer.name}': el material "
                f"'{layer.material}' no esta en la biblioteca cargada."
            )
        w = _cell_widths(layer.thickness, layer.n_cells, layer.grading)
        widths.append(w)
        mi = material_names.index(layer.material)
        mat_index.extend([mi] * layer.n_cells)
        layer_index.extend([li] * layer.n_cells)
        # La resistencia de contacto de una capa vive en su cara fria.
        interface_r.extend([0.0] * (layer.n_cells - 1) + [layer.contact_resistance])

    dx = np.concatenate(widths)
    n = dx.size
    edges = np.concatenate(([0.0], np.cumsum(dx)))          # profundidad de caras

    if section.geometry == "cylindrical":
        height = float(section.height)
        x_face = float(section.inner_radius) + edges
        x_node = 0.5 * (x_face[:-1] + x_face[1:])
        face_area = 2.0 * math.pi * x_face * height
        volume = math.pi * (x_face[1:] ** 2 - x_face[:-1] ** 2) * height
        g_minus = np.log(x_node / x_face[:-1]) / (2.0 * math.pi * height)
        g_plus = np.log(x_face[1:] / x_node) / (2.0 * math.pi * height)
    else:
        area = float(section.area)
        x_face = edges.copy()
        x_node = 0.5 * (x_face[:-1] + x_face[1:])
        face_area = np.full(n + 1, area)
        volume = dx * area
        g_minus = (x_node - x_face[:-1]) / area
        g_plus = (x_face[1:] - x_node) / area

    # Resistencia de contacto por cara [K/W]: la cara j (1..n-1) esta entre las
    # celdas j-1 y j; la resistencia declarada pertenece a la celda j-1.
    contact_R = np.zeros(n + 1)
    inner_r = np.asarray(interface_r[:-1], dtype=float)     # se descarta la ultima (cara externa)
    if n > 1:
        contact_R[1:n] = inner_r / face_area[1:n]

    depth_node = 0.5 * (edges[:-1] + edges[1:])

    return Mesh(
        section_name=section.name,
        geometry=section.geometry,
        x_face=x_face,
        x_node=x_node,
        depth_node=depth_node,
        volume=volume,
        face_area=face_area,
        g_minus=g_minus,
        g_plus=g_plus,
        contact_R=contact_R,
        mat_index=np.asarray(mat_index, dtype=int),
        layer_index=np.asarray(layer_index, dtype=int),
        material_names=material_names,
        layer_names=tuple(layer.name for layer in section.layers),
    )
