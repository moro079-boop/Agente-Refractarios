import numpy as np
import pytest

from ladle_thermal.materials import Material, PropertyTable, load_materials


def test_library_loads_and_every_material_has_a_source(library):
    assert len(library) >= 7
    for material in library:
        assert material.source, f"{material.name} sin fuente documentada"
        assert material.density > 0


def test_material_without_source_is_rejected():
    with pytest.raises(ValueError, match="source"):
        Material.from_spec("fantasma", {"density": 3000, "conductivity": 2.0, "specific_heat": 1000})


def test_property_table_interpolates_and_clamps():
    table = PropertyTable(np.array([300.0, 800.0]), np.array([2.0, 1.0]), "k")
    assert table(300.0) == pytest.approx(2.0)
    assert table(550.0) == pytest.approx(1.5)
    assert table(100.0) == pytest.approx(2.0)    # extrapolacion plana
    assert table(2000.0) == pytest.approx(1.0)


def test_property_table_rejects_inconsistent_input():
    with pytest.raises(ValueError):
        PropertyTable(np.array([300.0, 200.0]), np.array([1.0, 2.0]), "mala")
    with pytest.raises(ValueError):
        PropertyTable(np.array([300.0, 400.0]), np.array([1.0]), "mala")
    with pytest.raises(ValueError):
        PropertyTable(np.array([300.0]), np.array([-1.0]), "mala")


def test_enthalpy_matches_numerical_integration(library):
    material = library["alumina_spinel_castable"]
    t_ref, t_end = 298.15, 1373.15
    grid = np.linspace(t_ref, t_end, 20001)
    reference = float(np.trapezoid(material.density * material.cp(grid), grid))
    assert material.enthalpy_per_volume(t_end, t_ref) == pytest.approx(reference, rel=1e-6)


def test_enthalpy_is_vectorised_and_monotonic(library):
    material = library["carbon_steel_shell"]
    temps = np.array([400.0, 600.0, 900.0])
    values = material.enthalpy_per_volume(temps)
    assert values.shape == temps.shape
    assert np.all(np.diff(values) > 0)


def test_diffusivity_order_of_magnitude(library):
    # Refractario denso: alpha ~ 1e-7 a 1e-6 m2/s. Acero: ~1e-5.
    castable = library["alumina_spinel_castable"].diffusivity(1373.15)
    steel = library["carbon_steel_shell"].diffusivity(573.15)
    assert 1e-7 < castable < 1e-6
    assert 5e-6 < steel < 2e-5
    assert steel > 10 * castable


def test_unknown_material_error_lists_options(library):
    with pytest.raises(KeyError, match="Disponibles"):
        library["no_existe"]
