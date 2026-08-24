import numpy as np
import pytest

from ladle_thermal.boundary import AmbientShell, EmptyLadleCavity, LiquidSteelBath, PreheaterBurner
from ladle_thermal.cycle import Segment, run_segments, uniform_state
from ladle_thermal.preheat import ReadinessCriterion, required_preheat_time
from ladle_thermal.solver import SolverOptions, steady_state
from ladle_thermal.study import CoolingScenario, build_preheat_map, cyclic_steady_state

OPTS = SolverOptions(dt=45.0, dt_initial=0.5, dt_growth=1.35)


@pytest.fixture(scope="module")
def burner():
    return PreheaterBurner(gas_temperature_C=1300, burner_power_MW=4.0, heated_area=45.7)


@pytest.fixture(scope="module")
def shell():
    return AmbientShell(35.0, 0.80, 3.4)


def test_criterion_describes_both_conditions():
    assert "1100" in ReadinessCriterion().describe()
    full = ReadinessCriterion(1100.0, 1000.0, 50.0)
    assert "50 mm" in full.describe()
    with pytest.raises(ValueError):
        ReadinessCriterion(depth_mm=0.0)


def test_early_stop_matches_full_simulation(wall_mesh, materials, burner, shell):
    start = uniform_state(wall_mesh, 700.0)
    crit = ReadinessCriterion(1100.0, 1000.0, 50.0)
    kw = dict(max_time=12 * 3600.0, bc_cold=shell, options=OPTS)
    fast = required_preheat_time(wall_mesh, materials, start, burner, crit, early_stop=True, **kw)
    slow = required_preheat_time(wall_mesh, materials, start, burner, crit, early_stop=False, **kw)
    assert fast.criterion_met and slow.criterion_met
    assert fast.time_min == pytest.approx(slow.time_min, abs=0.5)


def test_preheat_time_grows_with_how_cold_the_lining_is(wall_mesh, materials, burner, shell):
    crit = ReadinessCriterion(1100.0, 1000.0, 50.0)
    times = []
    for start_C in (1000.0, 800.0, 600.0, 400.0):
        result = required_preheat_time(
            wall_mesh, materials, uniform_state(wall_mesh, start_C), burner, crit,
            max_time=16 * 3600.0, bc_cold=shell, options=OPTS)
        assert result.criterion_met
        times.append(result.time_min)
    assert times == sorted(times), f"el tiempo de precalentador debe crecer al enfriarse: {times}"


def test_a_bigger_burner_needs_less_time(wall_mesh, materials, shell):
    crit = ReadinessCriterion(1100.0, 1000.0, 50.0)
    start = uniform_state(wall_mesh, 600.0)
    kw = dict(max_time=20 * 3600.0, bc_cold=shell, options=OPTS)
    small = required_preheat_time(wall_mesh, materials, start,
                                  PreheaterBurner(gas_temperature_C=1300, burner_power_MW=2.0,
                                                  heated_area=45.7), crit, **kw)
    big = required_preheat_time(wall_mesh, materials, start,
                                PreheaterBurner(gas_temperature_C=1300, burner_power_MW=8.0,
                                                heated_area=45.7), crit, **kw)
    assert big.time_min < small.time_min


def test_unreachable_criterion_reports_failure(wall_mesh, materials, shell):
    """Un quemador pequeno no puede llevar el revestimiento a 1500 C."""
    weak = PreheaterBurner(gas_temperature_C=900, burner_power_MW=0.5, heated_area=45.7)
    result = required_preheat_time(
        wall_mesh, materials, uniform_state(wall_mesh, 300.0), weak,
        ReadinessCriterion(hot_face_C=1500.0), max_time=2 * 3600.0, bc_cold=shell, options=OPTS)
    assert not result.criterion_met
    assert result.time_s is None
    assert "NO se alcanza" in result.summary()


def test_depth_criterion_is_the_binding_one_after_a_long_wait(wall_mesh, materials, burner, shell):
    """La cara se recupera en minutos; la masa termica detras, no."""
    result = required_preheat_time(
        wall_mesh, materials, uniform_state(wall_mesh, 500.0), burner,
        ReadinessCriterion(1100.0, 1000.0, 50.0),
        max_time=20 * 3600.0, bc_cold=shell, options=OPTS)
    assert result.criterion_met
    assert result.limiting == "media_50mm_C"

    face_only = required_preheat_time(
        wall_mesh, materials, uniform_state(wall_mesh, 500.0), burner,
        ReadinessCriterion(hot_face_C=1100.0),
        max_time=20 * 3600.0, bc_cold=shell, options=OPTS)
    assert face_only.time_min < result.time_min


def test_cyclic_steady_state_converges_and_sits_between_bounds(wall_mesh, materials, shell):
    segments = [
        Segment("colada", 60 * 60.0, LiquidSteelBath(1620.0, h=1500.0)),
        Segment("vacia", 45 * 60.0, EmptyLadleCavity.from_section(1.6, 3.75)),
    ]
    result = cyclic_steady_state(wall_mesh, materials, segments, shell, OPTS,
                                 initial_C=150.0, max_cycles=40, tolerance_K=1.0)
    assert result.converged, f"deriva {result.drift_K:.2f} K tras {result.cycles} ciclos"
    hot_bound = steady_state(wall_mesh, materials, LiquidSteelBath(1620.0), shell)
    assert 150.0 < result.hot_face_C < hot_bound[0] - 273.15
    # La carcasa periodica debe quedar en un rango industrial creible
    assert 60.0 < result.state[-1] - 273.15 < 400.0


def test_preheat_map_is_monotonic_and_lid_helps(wall_mesh, materials, burner, shell):
    start = steady_state(wall_mesh, materials, LiquidSteelBath(1620.0), shell)
    scenarios = [
        CoolingScenario("sin_tapa", EmptyLadleCavity.from_section(1.6, 3.75)),
        CoolingScenario("con_tapa", EmptyLadleCavity.from_section(1.6, 3.75, lid_factor=0.35)),
    ]
    pmap = build_preheat_map(
        wall_mesh, materials, start, scenarios, [30, 120, 360],
        burner, ReadinessCriterion(1100.0, 1000.0, 50.0),
        bc_cold=shell, options=OPTS, max_preheat_h=20.0)

    matrix = pmap.matrix()
    assert matrix.shape == (2, 3)
    for row in matrix:
        assert np.all(np.diff(row) > 0), "mas espera debe exigir mas precalentador"
    assert np.all(matrix[1] < matrix[0]), "la tapa debe reducir el precalentamiento"

    assert "| Escenario |" in pmap.to_markdown()
    assert len(pmap.to_csv_rows()) == 7
    for entry in pmap.entries:
        assert entry.hot_face_after_cooling_C < 1620.0
        assert entry.energy_deficit_MJ >= 0.0
