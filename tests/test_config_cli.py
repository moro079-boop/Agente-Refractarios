"""Los archivos de configuracion del repo deben cargar y ser coherentes."""

import math

import pytest

from ladle_thermal.boundary import EmptyLadleCavity, LiquidSteelBath, PreheaterBurner
from ladle_thermal.cli import build_parser, main
from ladle_thermal.geometry import load_ladle
from ladle_thermal.scenarios import load_study

STUDIES = ("precalentamiento_base", "criterio_solo_cara")


@pytest.fixture(scope="module")
def ladle(repo_root):
    return load_ladle(repo_root / "config" / "olla_acero_150t.yaml")


def test_ladle_config_is_consistent(ladle):
    assert set(ladle.sections) == {"wall", "bottom"}
    wall = ladle["wall"]
    assert wall.layers[0].name == "revestimiento_trabajo"
    assert wall.layers[-1].material == "carbon_steel_shell"
    assert 0.2 < wall.total_thickness < 0.6
    # El area declarada del fondo debe cuadrar con el radio interior de la pared
    assert ladle["bottom"].area == pytest.approx(math.pi * wall.inner_radius ** 2, rel=0.02)


def test_layers_are_ordered_hot_to_cold(ladle, library):
    """Cada capa hacia afuera debe tolerar menos temperatura que la anterior."""
    for section in ladle.sections.values():
        limits = [library[l.material].max_service_C for l in section.layers]
        assert all(a is not None for a in limits)
        assert limits == sorted(limits, reverse=True), f"orden de capas sospechoso en '{section.name}'"


@pytest.mark.parametrize("name", STUDIES)
def test_study_loads_and_builds_every_object(repo_root, name):
    config = load_study(repo_root / "config" / "studies" / f"{name}.yaml")
    assert config.mesh.n_cells > 20
    assert config.criterion().hot_face_C == 1100.0
    assert isinstance(config.preheater(), PreheaterBurner)
    assert config.preheater().power_limited, "el quemador del estudio debe tener potencia finita"
    scenarios = config.cooling_scenarios()
    assert len(scenarios) >= 2
    assert all(isinstance(s.bc, EmptyLadleCavity) for s in scenarios)
    assert config.cooling_times_min()[0] == 0.0
    assert config.describe()


def test_cycle_segments_cover_a_real_rotation(repo_root):
    config = load_study(repo_root / "config" / "studies" / "precalentamiento_base.yaml")
    segments = config.cycle_segments()
    kinds = [type(s.bc_hot) for s in segments]
    assert LiquidSteelBath in kinds and EmptyLadleCavity in kinds and PreheaterBurner in kinds
    total_h = sum(s.duration for s in segments) / 3600.0
    assert 1.0 < total_h < 12.0, "un ciclo de olla realista dura entre 1 y 12 h"


def test_cavity_area_matches_geometry(repo_root):
    config = load_study(repo_root / "config" / "studies" / "precalentamiento_base.yaml")
    radius = config.section.inner_radius
    expected = 2 * math.pi * radius * config.cavity_depth + math.pi * radius ** 2
    assert config.cavity_area == pytest.approx(expected)
    assert config.preheater().heated_area == pytest.approx(expected)


def test_unknown_boundary_type_gives_a_helpful_error(repo_root):
    config = load_study(repo_root / "config" / "studies" / "precalentamiento_base.yaml")
    with pytest.raises(ValueError, match="Validos"):
        config.build_bc({"type": "horno_de_microondas"})


def test_unknown_initial_state_mode(repo_root):
    config = load_study(repo_root / "config" / "studies" / "precalentamiento_base.yaml")
    config.raw["initial_state"] = {"mode": "inventado"}
    with pytest.raises(ValueError, match="Validos"):
        config.initial_state()


def test_cli_describe_and_validate(repo_root, capsys):
    study = str(repo_root / "config" / "studies" / "precalentamiento_base.yaml")
    assert main(["describe", study]) == 0
    assert "olla_acero_150t" in capsys.readouterr().out
    assert main(["validate"]) == 0


def test_cli_parser_rejects_unknown_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["inventado"])
