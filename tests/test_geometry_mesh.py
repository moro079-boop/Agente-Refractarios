import math

import numpy as np
import pytest

from ladle_thermal.geometry import Layer, Section
from ladle_thermal.mesh import build_mesh


def test_cylindrical_mesh_volume_matches_analytic(wall_mesh, wall_section):
    r_in = wall_section.inner_radius
    r_out = wall_section.outer_radius
    exact = math.pi * (r_out ** 2 - r_in ** 2) * wall_section.height
    assert wall_mesh.total_volume == pytest.approx(exact, rel=1e-12)


def test_face_areas_and_layer_thicknesses(wall_mesh, wall_section):
    assert wall_mesh.hot_area == pytest.approx(wall_section.hot_area, rel=1e-12)
    assert wall_mesh.cold_area == pytest.approx(wall_section.cold_area, rel=1e-12)
    for li, layer in enumerate(wall_section.layers):
        cells = np.where(wall_mesh.layer_index == li)[0]
        thickness = wall_mesh.x_face[cells[-1] + 1] - wall_mesh.x_face[cells[0]]
        assert thickness == pytest.approx(layer.thickness, rel=1e-12)


def test_planar_mesh_volume(material_names):
    section = Section("bottom", (Layer("c", "alumina_spinel_castable", 0.25, 10),),
                      "planar", area=8.04)
    mesh = build_mesh(section, material_names)
    assert mesh.total_volume == pytest.approx(0.25 * 8.04, rel=1e-12)
    assert np.allclose(mesh.face_area, 8.04)


def test_grading_refines_the_hot_face(material_names):
    section = Section("w", (Layer("c", "alumina_spinel_castable", 0.20, 10, grading=1.3),),
                      "planar", area=1.0)
    mesh = build_mesh(section, material_names)
    widths = np.diff(mesh.x_face)
    assert widths[0] < widths[-1]
    assert np.all(np.diff(widths) > 0)
    assert widths.sum() == pytest.approx(0.20, rel=1e-12)


def test_contact_resistance_lands_on_the_right_face(material_names):
    section = Section("w", (
        Layer("a", "alumina_spinel_castable", 0.10, 4, contact_resistance=0.01),
        Layer("b", "high_alumina_brick_70", 0.10, 4)), "planar", area=2.0)
    mesh = build_mesh(section, material_names)
    assert mesh.contact_R[4] == pytest.approx(0.01 / 2.0)
    others = np.delete(mesh.contact_R, 4)
    assert np.allclose(others, 0.0)


def test_geometry_validation_errors(material_names):
    with pytest.raises(ValueError, match="inner_radius"):
        Section("w", (Layer("c", "x", 0.1),), "cylindrical", height=3.0)
    with pytest.raises(ValueError, match="area"):
        Section("w", (Layer("c", "x", 0.1),), "planar")
    with pytest.raises(ValueError, match="espesor"):
        Layer("c", "x", -0.1)
    with pytest.raises(KeyError, match="no esta en la biblioteca"):
        build_mesh(Section("w", (Layer("c", "inventado", 0.1),), "planar", area=1.0), material_names)


def test_depth_average_uses_volume_weighting(wall_mesh):
    values = np.linspace(1000.0, 500.0, wall_mesh.n_cells)
    mean = wall_mesh.depth_average(values, 0.050)
    inside = wall_mesh.cells_within_depth(0.050)
    assert inside.sum() > 1
    assert values[inside].min() <= mean <= values[inside].max()
