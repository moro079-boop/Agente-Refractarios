import math

import numpy as np
import pytest

from ladle_thermal.boundary import (
    AmbientShell,
    EmptyLadleCavity,
    LiquidSteelBath,
    PreheaterBurner,
    cavity_apparent_emissivity,
    radiative_coefficient,
    wall_to_mouth_view_factor,
)
from ladle_thermal.units import SIGMA, T0_K


def test_radiative_linearisation_is_exact():
    ts, te, eps = 1373.15, 308.15, 0.85
    h = radiative_coefficient(ts, te, eps)
    assert h * (te - ts) == pytest.approx(eps * SIGMA * (te ** 4 - ts ** 4), rel=1e-12)


def test_view_factor_is_bounded_and_decreases_with_depth():
    shallow = wall_to_mouth_view_factor(1.6, 1.0)
    deep = wall_to_mouth_view_factor(1.6, 6.0)
    assert 0.0 < deep < shallow < 1.0
    with pytest.raises(ValueError):
        wall_to_mouth_view_factor(1.6, 0.0)


def test_cavity_apparent_emissivity_limits():
    assert cavity_apparent_emissivity(1.0, 8.0, 46.0) == pytest.approx(1.0)
    # Una cavidad profunda con eps moderada se comporta casi como cuerpo negro
    assert cavity_apparent_emissivity(0.85, 8.0, 46.0) > 0.95
    # Sin cavidad (boca = toda la superficie) recupera la emisividad de la superficie
    assert cavity_apparent_emissivity(0.6, 10.0, 10.0) == pytest.approx(0.6)


def test_two_independent_cavity_models_agree_within_15_percent():
    radius, depth, eps = 1.60, 3.75, 0.85
    view = eps * wall_to_mouth_view_factor(radius, depth)
    mouth = math.pi * radius ** 2
    cavity = 2.0 * math.pi * radius * depth + mouth
    apparent = cavity_apparent_emissivity(eps, mouth, cavity) * mouth / cavity
    assert abs(view - apparent) / apparent < 0.15


def test_lid_reduces_radiative_exchange_proportionally():
    open_ladle = EmptyLadleCavity.from_section(1.6, 3.75)
    lidded = EmptyLadleCavity.from_section(1.6, 3.75, lid_factor=0.35)
    assert lidded.exchange_factor == pytest.approx(0.35 * open_ladle.exchange_factor)
    hot = 1400.0 + T0_K
    assert lidded.coefficient(hot) < open_ladle.coefficient(hot)


def test_cavity_requires_geometry_or_override():
    with pytest.raises(ValueError, match="mouth_area"):
        EmptyLadleCavity(ambient_C=35.0)
    with pytest.raises(ValueError, match="lid_factor"):
        EmptyLadleCavity.from_section(1.6, 3.75, lid_factor=1.5)


def test_burner_energy_balance_closes():
    """Lo que ceden los gases debe igualar lo que absorbe el revestimiento."""
    burner = PreheaterBurner(gas_temperature_C=1400, burner_power_MW=4.0,
                             adiabatic_flame_C=1900, heated_area=45.7)
    t_ad = burner.adiabatic_flame_C + T0_K
    m_cp = burner.burner_power_MW * 1e6 / (t_ad - (burner.ambient_C + T0_K))
    for t_surface_C in (100, 500, 900, 1200):
        ts = t_surface_C + T0_K
        tg = burner.gas_temperature(ts)
        released = m_cp * (t_ad - tg)
        absorbed = burner.heated_area * burner._specific_flux(tg, ts)
        assert released == pytest.approx(absorbed, rel=1e-5)


def test_burner_efficiency_falls_as_lining_heats():
    burner = PreheaterBurner(gas_temperature_C=1400, burner_power_MW=4.0, heated_area=45.7)
    efficiencies = [burner.thermal_efficiency(t + T0_K) for t in (200, 600, 1000, 1200)]
    assert all(0.0 < e < 1.0 for e in efficiencies)
    assert efficiencies == sorted(efficiencies, reverse=True)


def test_power_limited_burner_is_weaker_than_imposed_gas_temperature():
    ts = 600.0 + T0_K
    unlimited = PreheaterBurner(gas_temperature_C=1300)
    limited = PreheaterBurner(gas_temperature_C=1300, burner_power_MW=2.0, heated_area=45.7)
    assert limited.gas_temperature(ts) < unlimited.gas_temperature(ts)
    assert limited.flux(ts) < unlimited.flux(ts)


def test_bigger_burner_gives_more_flux():
    ts = 600.0 + T0_K
    small = PreheaterBurner(gas_temperature_C=1400, burner_power_MW=2.0, heated_area=45.7)
    big = PreheaterBurner(gas_temperature_C=1400, burner_power_MW=8.0, heated_area=45.7)
    assert big.flux(ts) > small.flux(ts)


def test_burner_ramp_and_schedule():
    ramped = PreheaterBurner(gas_temperature_C=1200, ramp_C_per_h=150, start_temperature_C=30)
    assert ramped.env_temperature(0.0) == pytest.approx(30 + T0_K)
    assert ramped.env_temperature(3600.0) == pytest.approx(180 + T0_K)
    assert ramped.env_temperature(1e6) == pytest.approx(1200 + T0_K)   # satura en el setpoint

    scheduled = PreheaterBurner(schedule_C=((0, 100), (60, 700), (180, 1250)))
    assert scheduled.env_temperature(0.0) == pytest.approx(100 + T0_K)
    assert scheduled.env_temperature(30 * 60.0) == pytest.approx(400 + T0_K)
    with pytest.raises(ValueError, match="crecientes"):
        PreheaterBurner(schedule_C=((60, 700), (0, 100)))


def test_shell_convection_is_physically_plausible():
    shell = AmbientShell(ambient_C=35.0, emissivity=0.80, characteristic_length=3.4)
    for t_shell_C in (100, 200, 300, 400):
        h_nat = shell.natural_convection(t_shell_C + T0_K)
        assert 3.0 < h_nat < 20.0, f"h_nat={h_nat} fuera de rango a {t_shell_C} C"
    # A 300 C la radiacion debe dominar sobre la conveccion natural
    ts = 300 + T0_K
    assert radiative_coefficient(ts, 35 + T0_K, 0.80) > shell.natural_convection(ts)


def test_shell_flux_matches_industrial_order_of_magnitude():
    shell = AmbientShell(ambient_C=35.0, emissivity=0.80, characteristic_length=3.4)
    flux = -shell.flux(300 + T0_K) / 1000.0     # kW/m2 salientes
    assert 4.0 < flux < 12.0


def test_wind_increases_losses():
    still = AmbientShell(35.0, 0.8, 3.4)
    windy = AmbientShell(35.0, 0.8, 3.4, wind_speed=6.0)
    assert windy.coefficient(300 + T0_K) > still.coefficient(300 + T0_K)


def test_liquid_steel_bath_cools_over_time():
    bath = LiquidSteelBath(1620.0, h=1500.0, cooling_rate_C_per_min=0.5)
    assert bath.env_temperature(0.0) == pytest.approx(1620 + T0_K)
    assert bath.env_temperature(3600.0) == pytest.approx(1590 + T0_K)
