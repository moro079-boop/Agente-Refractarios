import numpy as np
import pytest

from ladle_thermal.boundary import Adiabatic, AmbientShell, Convection, EmptyLadleCavity, LiquidSteelBath
from ladle_thermal.cycle import Segment, run_segments, uniform_state
from ladle_thermal.solver import SolverOptions, internal_energy, steady_state, tdma


def test_tdma_matches_dense_solve():
    rng = np.random.default_rng(0)
    n = 25
    diag = rng.uniform(5.0, 10.0, n)
    lower = np.concatenate(([0.0], -rng.uniform(0.5, 2.0, n - 1)))
    upper = np.concatenate((-rng.uniform(0.5, 2.0, n - 1), [0.0]))
    rhs = rng.uniform(-10.0, 10.0, n)
    dense = np.diag(diag) + np.diag(lower[1:], -1) + np.diag(upper[:-1], 1)
    assert np.allclose(tdma(lower, diag, upper, rhs), np.linalg.solve(dense, rhs))


def test_tdma_single_cell():
    assert tdma(np.array([0.0]), np.array([4.0]), np.array([0.0]), np.array([8.0]))[0] == pytest.approx(2.0)


def test_adiabatic_section_conserves_energy(wall_mesh, materials):
    start = uniform_state(wall_mesh, 900.0)
    history = run_segments(wall_mesh, materials, [Segment("aislada", 7200.0, Adiabatic())],
                           start, Adiabatic(), SolverOptions(dt=60.0, dt_initial=1.0))
    before = internal_energy(wall_mesh, materials, history.initial_state)
    after = internal_energy(wall_mesh, materials, history.final_state)
    assert after == pytest.approx(before, rel=1e-5)


def test_surface_temperature_lies_between_medium_and_first_node(wall_mesh, materials):
    """Con resistencia de pelicula finita la cara no puede alcanzar el medio."""
    bath = LiquidSteelBath(1600.0, h=1500.0)
    history = run_segments(wall_mesh, materials, [Segment("llenado", 600.0, bath)],
                           uniform_state(wall_mesh, 400.0), AmbientShell(),
                           SolverOptions(dt=5.0, dt_initial=0.05))
    for i in range(1, history.times.size):
        node = history.temperatures[i, 0]
        surface = history.hot_surface_K[i]
        assert node < surface < bath.env_temperature(0.0) + 1e-6


def test_steady_state_matches_long_transient(wall_mesh, materials):
    bath = LiquidSteelBath(1600.0, h=1500.0)
    shell = AmbientShell(35.0, 0.8, 3.4)
    direct = steady_state(wall_mesh, materials, bath, shell)
    transient = run_segments(wall_mesh, materials, [Segment("largo", 200 * 3600.0, bath)],
                             uniform_state(wall_mesh, 600.0), shell,
                             SolverOptions(dt=600.0, dt_initial=1.0)).final_state
    assert np.max(np.abs(direct - transient)) < 1.5


def test_cooling_is_monotonic_and_lid_slows_it(wall_mesh, materials):
    shell = AmbientShell(35.0, 0.8, 3.4)
    start = steady_state(wall_mesh, materials, LiquidSteelBath(1620.0), shell)
    opts = SolverOptions(dt=30.0, dt_initial=0.5)
    open_h = run_segments(wall_mesh, materials,
                          [Segment("abierta", 4 * 3600.0, EmptyLadleCavity.from_section(1.6, 3.75))],
                          start, shell, opts)
    lid_h = run_segments(wall_mesh, materials,
                         [Segment("tapada", 4 * 3600.0,
                                  EmptyLadleCavity.from_section(1.6, 3.75, lid_factor=0.35))],
                         start, shell, opts)
    assert np.all(np.diff(open_h.hot_face_C) <= 1e-6)          # enfriamiento monotono
    assert lid_h.hot_face_C[-1] > open_h.hot_face_C[-1] + 50   # la tapa conserva calor
    assert open_h.q_hot[1] < 0                                  # la olla pierde calor por la boca


def test_timestep_refinement_changes_little(wall_mesh, materials):
    shell = AmbientShell(35.0, 0.8, 3.4)
    start = uniform_state(wall_mesh, 1300.0)
    cavity = EmptyLadleCavity.from_section(1.6, 3.75)
    coarse = run_segments(wall_mesh, materials, [Segment("e", 3600.0, cavity)], start, shell,
                          SolverOptions(dt=120.0, dt_initial=1.0)).hot_face_C[-1]
    fine = run_segments(wall_mesh, materials, [Segment("e", 3600.0, cavity)], start, shell,
                        SolverOptions(dt=5.0, dt_initial=0.05)).hot_face_C[-1]
    assert abs(coarse - fine) < 3.0


def test_segments_chain_state(wall_mesh, materials):
    shell = AmbientShell(35.0, 0.8, 3.4)
    history = run_segments(wall_mesh, materials, [
        Segment("colada", 1800.0, LiquidSteelBath(1620.0)),
        Segment("vacia", 1800.0, EmptyLadleCavity.from_section(1.6, 3.75)),
    ], uniform_state(wall_mesh, 800.0), shell, SolverOptions(dt=30.0, dt_initial=0.5))
    assert history.segment_names == ("colada", "vacia")
    start, end = history.segment_bounds("vacia")
    assert start == pytest.approx(1800.0, abs=60.0)
    assert end == pytest.approx(3600.0, abs=1e-6)
    # La cara caliente sube durante la colada y baja durante la espera
    colada = history.segment_index == 0
    assert history.hot_face_C[colada][-1] > history.hot_face_C[colada][0]
    assert history.hot_face_C[-1] < history.hot_face_C[colada][-1]


def test_state_at_interpolates(wall_mesh, materials):
    history = run_segments(wall_mesh, materials, [Segment("e", 1200.0, Convection(20.0, 100.0))],
                           uniform_state(wall_mesh, 900.0), Adiabatic(),
                           SolverOptions(dt=30.0, dt_initial=1.0))
    assert np.allclose(history.state_at(-10.0), history.initial_state)
    assert np.allclose(history.state_at(1e9), history.final_state)
    mid = history.state_at(600.0)
    assert np.all(mid <= history.initial_state + 1e-9)
    assert np.all(mid >= history.final_state - 1e-9)


def test_all_steps_converge(wall_mesh, materials):
    history = run_segments(wall_mesh, materials,
                           [Segment("dura", 3600.0, EmptyLadleCavity.from_section(1.6, 3.75))],
                           uniform_state(wall_mesh, 1500.0), AmbientShell(35.0, 0.8, 3.4),
                           SolverOptions(dt=60.0, dt_initial=0.5))
    assert history.non_converged_steps == 0


def test_mismatched_initial_state_is_rejected(wall_mesh, materials):
    with pytest.raises(ValueError, match="estado inicial"):
        run_segments(wall_mesh, materials, [Segment("x", 60.0, Adiabatic())],
                     np.zeros(3), Adiabatic())
