"""Condiciones de frontera en las caras caliente y fria de una seccion.

Todas las condiciones se expresan de forma unificada como

    q'' = h_eff(T_s, t) * (T_env(t) - T_s)          [W/m2, positivo hacia la pared]

donde la parte radiativa se linealiza de forma EXACTA mediante

    sigma*(Te^4 - Ts^4) = sigma*(Te^2 + Ts^2)*(Te + Ts)*(Te - Ts)

lo que convierte la radiacion en un coeficiente dependiente de T_s. El solver
itera sobre h_eff hasta converger, de modo que la linealizacion no introduce
error de modelo, solo requiere iteracion.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .units import GRAVITY, SIGMA, T0_K, air_properties

_H_FIXED = 1.0e9   # coeficiente "infinito" para imponer temperatura


def _interp_schedule(t: float, points: Sequence[tuple[float, float]]) -> float:
    """Interpola una rampa definida como [(t_s, T_K), ...]; plana fuera del rango."""
    ts = [p[0] for p in points]
    vs = [p[1] for p in points]
    return float(np.interp(t, ts, vs))


def radiative_coefficient(t_surface_k: float, t_env_k: float, exchange_factor: float) -> float:
    """Coeficiente radiativo equivalente [W/m2K]. Linealizacion exacta."""
    if exchange_factor <= 0.0:
        return 0.0
    ts = max(float(t_surface_k), 1.0)
    te = max(float(t_env_k), 1.0)
    return exchange_factor * SIGMA * (ts * ts + te * te) * (ts + te)


def wall_to_mouth_view_factor(radius: float, depth: float) -> float:
    """Factor de vista de la pared lateral hacia la boca abierta de la olla.

    Se modela la cavidad como un cilindro de radio `radius` y profundidad
    `depth` con la boca abierta arriba y el fondo cerrado. Se usa la relacion
    clasica entre dos discos coaxiales iguales y despues reciprocidad:

        F_pared->boca = R * (1 - F_disco-disco) / (2 * L)

    Devuelve un valor puramente geometrico en [0, 1].
    """
    if radius <= 0 or depth <= 0:
        raise ValueError("radius y depth deben ser > 0")
    r = radius / depth
    s = 1.0 + (1.0 + r * r) / (r * r)
    f_disks = 0.5 * (s - math.sqrt(max(s * s - 4.0, 0.0)))
    return float(radius * (1.0 - f_disks) / (2.0 * depth))


def cavity_apparent_emissivity(surface_emissivity: float, mouth_area: float, cavity_area: float) -> float:
    """Emisividad aparente de una cavidad isoterma vista desde su boca.

        eps_app = eps / (eps + (1 - eps) * A_boca / A_cavidad)
    """
    if not 0.0 < surface_emissivity <= 1.0:
        raise ValueError("surface_emissivity debe estar en (0, 1]")
    ratio = mouth_area / cavity_area
    return float(surface_emissivity / (surface_emissivity + (1.0 - surface_emissivity) * ratio))


class SurfaceBC(ABC):
    """Interfaz de una condicion de frontera superficial."""

    name: str = "bc"

    @abstractmethod
    def env_temperature(self, t: float = 0.0) -> float:
        """Temperatura del medio [K] en el instante t [s]."""

    @abstractmethod
    def coefficient(self, t_surface_k: float, t: float = 0.0) -> float:
        """Coeficiente global de transferencia h_eff [W/m2K]."""

    def flux(self, t_surface_k: float, t: float = 0.0) -> float:
        """Flujo hacia la pared [W/m2] (positivo = entra calor)."""
        return self.coefficient(t_surface_k, t) * (self.env_temperature(t) - t_surface_k)

    def describe(self) -> str:
        return f"{self.name}"


@dataclass
class Adiabatic(SurfaceBC):
    """Sin intercambio de calor. Util para estudios de sensibilidad."""

    name: str = "adiabatica"

    def env_temperature(self, t: float = 0.0) -> float:
        return 0.0

    def coefficient(self, t_surface_k: float, t: float = 0.0) -> float:
        return 0.0

    def describe(self) -> str:
        return "Adiabatica (sin perdidas)"


@dataclass
class FixedTemperature(SurfaceBC):
    """Temperatura de superficie impuesta (Dirichlet)."""

    temperature_C: float = 1600.0
    name: str = "temperatura_impuesta"

    def env_temperature(self, t: float = 0.0) -> float:
        return self.temperature_C + T0_K

    def coefficient(self, t_surface_k: float, t: float = 0.0) -> float:
        return _H_FIXED

    def describe(self) -> str:
        return f"Temperatura impuesta {self.temperature_C:.0f} C"


@dataclass
class Convection(SurfaceBC):
    """Conveccion pura con coeficiente constante."""

    h: float = 10.0
    temperature_C: float = 25.0
    name: str = "conveccion"

    def env_temperature(self, t: float = 0.0) -> float:
        return self.temperature_C + T0_K

    def coefficient(self, t_surface_k: float, t: float = 0.0) -> float:
        return self.h

    def describe(self) -> str:
        return f"Conveccion h={self.h:.1f} W/m2K a {self.temperature_C:.0f} C"


@dataclass
class LiquidSteelBath(SurfaceBC):
    """Cara caliente en contacto con acero liquido.

    El bano esta fuertemente agitado (burbujeo de argon, llenado), de modo que
    el transporte hacia el revestimiento esta dominado por conveccion con un
    coeficiente alto: la cara caliente alcanza casi la temperatura del acero en
    los primeros segundos. `cooling_rate_C_per_min` permite representar la
    caida de temperatura del bano durante la retencion.
    """

    steel_temperature_C: float = 1600.0
    h: float = 1500.0
    cooling_rate_C_per_min: float = 0.0
    name: str = "acero_liquido"

    def env_temperature(self, t: float = 0.0) -> float:
        return self.steel_temperature_C - self.cooling_rate_C_per_min * (t / 60.0) + T0_K

    def coefficient(self, t_surface_k: float, t: float = 0.0) -> float:
        return self.h

    def describe(self) -> str:
        txt = f"Acero liquido {self.steel_temperature_C:.0f} C, h={self.h:.0f} W/m2K"
        if self.cooling_rate_C_per_min:
            txt += f", enfriando {self.cooling_rate_C_per_min:.2f} C/min"
        return txt


@dataclass
class EmptyLadleCavity(SurfaceBC):
    """Olla vacia enfriandose: radiacion por la boca + conveccion interna.

    Modelo: la cavidad se trata como aproximadamente isoterma (hipotesis
    razonable para una olla recien vaciada, donde pared y fondo salen del mismo
    ciclo termico). La perdida radiativa total escapa por la boca con la
    emisividad aparente de cavidad, y se reparte sobre el area interior:

        q''_rad = eps_app * (A_boca / A_cavidad) * sigma * (T_amb^4 - T_s^4)

    `lid_factor` (0-1) multiplica ese intercambio cuando la olla lleva tapa.
    Es el principal parametro de calibracion del modelo: con termopar en la
    carcasa y una curva de enfriamiento real se ajusta en minutos.
    """

    ambient_C: float = 35.0
    emissivity: float = 0.85
    mouth_area: float = 0.0
    cavity_area: float = 0.0
    h_conv: float = 10.0
    lid_factor: float = 1.0
    exchange_factor_override: float | None = None
    name: str = "olla_vacia"

    def __post_init__(self) -> None:
        if self.exchange_factor_override is None:
            if self.mouth_area <= 0 or self.cavity_area <= 0:
                raise ValueError(
                    "EmptyLadleCavity necesita mouth_area y cavity_area > 0, "
                    "o bien exchange_factor_override."
                )
        if not 0.0 <= self.lid_factor <= 1.0:
            raise ValueError("lid_factor debe estar en [0, 1]")

    @property
    def exchange_factor(self) -> float:
        """Factor de intercambio radiativo efectivo de la superficie interior."""
        if self.exchange_factor_override is not None:
            return float(self.exchange_factor_override) * self.lid_factor
        eps_app = cavity_apparent_emissivity(self.emissivity, self.mouth_area, self.cavity_area)
        return float(eps_app * (self.mouth_area / self.cavity_area) * self.lid_factor)

    @classmethod
    def from_section(
        cls,
        inner_radius: float,
        inner_depth: float,
        ambient_C: float = 35.0,
        emissivity: float = 0.85,
        h_conv: float = 10.0,
        lid_factor: float = 1.0,
        include_bottom: bool = True,
    ) -> "EmptyLadleCavity":
        """Construye la condicion a partir de la geometria interna de la olla."""
        mouth = math.pi * inner_radius ** 2
        cavity = 2.0 * math.pi * inner_radius * inner_depth + (mouth if include_bottom else 0.0)
        return cls(
            ambient_C=ambient_C,
            emissivity=emissivity,
            mouth_area=mouth,
            cavity_area=cavity,
            h_conv=h_conv,
            lid_factor=lid_factor,
        )

    def env_temperature(self, t: float = 0.0) -> float:
        return self.ambient_C + T0_K

    def coefficient(self, t_surface_k: float, t: float = 0.0) -> float:
        return self.h_conv + radiative_coefficient(t_surface_k, self.env_temperature(t), self.exchange_factor)

    def describe(self) -> str:
        tag = "con tapa" if self.lid_factor < 1.0 else "sin tapa"
        return (
            f"Olla vacia {tag}: F_rad={self.exchange_factor:.4f}, "
            f"h_conv={self.h_conv:.1f} W/m2K, ambiente {self.ambient_C:.0f} C"
        )


@dataclass
class PreheaterBurner(SurfaceBC):
    """Cara caliente en un precalentador de quemador.

    Dos modos, y la eleccion importa mas que cualquier otro parametro:

    1. `burner_power_MW = None` -> TEMPERATURA DE GAS IMPUESTA.
       q'' = h_conv*(Tg - Ts) + eps_eff*sigma*(Tg^4 - Ts^4)
       Equivale a un quemador de potencia infinita: los gases se mantienen a Tg
       por mucho calor que absorba el revestimiento. Sirve como LIMITE SUPERIOR
       (tiempo minimo teorico), no como prediccion de un precalentador real.

    2. `burner_power_MW` definido -> MODELO DE HORNO BIEN AGITADO.
       La temperatura de gas sale de un balance de energia sobre los gases:

           m_cp * (T_ad - T_g)  =  A * [ h_conv*(Tg - Ts) + eps*sigma*(Tg^4 - Ts^4) ]
           \_______________/       \_________________________________________/
            calor que ceden          calor que absorbe el revestimiento
            los gases al enfriarse
            de T_ad a T_g

       con m_cp = P_quemador / (T_ad - T_ambiente). Lo que no absorbe el
       revestimiento se va por la chimenea a T_g. Es el modelo clasico de horno
       bien agitado, y reproduce el comportamiento real: con revestimiento frio
       los gases se enfrian mucho y el flujo se autolimita; a medida que el
       refractario calienta, T_g sube y se acerca a la llama adiabatica.

    En el modo 2 la interfaz sigue siendo q'' = h_eff*(T_env - Ts), con
    T_env = T_ad fija y todo el comportamiento metido en h_eff. Asi el solver
    recupera la temperatura de cara sin estado oculto.
    """

    gas_temperature_C: float = 1250.0
    h_conv: float = 30.0
    eps_eff: float = 0.70
    ramp_C_per_h: float | None = None
    start_temperature_C: float | None = None
    schedule_C: tuple[tuple[float, float], ...] | None = None
    burner_power_MW: float | None = None
    adiabatic_flame_C: float = 1900.0
    heated_area: float = 40.0
    ambient_C: float = 25.0
    name: str = "precalentador"

    _schedule_k: tuple[tuple[float, float], ...] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.schedule_C:
            pts = tuple((float(m) * 60.0, float(c) + T0_K) for m, c in self.schedule_C)
            if any(pts[i][0] >= pts[i + 1][0] for i in range(len(pts) - 1)):
                raise ValueError("schedule_C debe tener tiempos estrictamente crecientes")
            object.__setattr__(self, "_schedule_k", pts)
        if self.burner_power_MW is not None:
            if self.burner_power_MW <= 0:
                raise ValueError("burner_power_MW debe ser > 0")
            if self.heated_area <= 0:
                raise ValueError("heated_area debe ser > 0")
            if self.adiabatic_flame_C <= self.ambient_C:
                raise ValueError("adiabatic_flame_C debe superar ambient_C")

    @property
    def power_limited(self) -> bool:
        return self.burner_power_MW is not None

    # ------------------------------------------------------ temperatura de gas
    def _setpoint_k(self, t: float) -> float:
        if self._schedule_k is not None:
            return _interp_schedule(t, self._schedule_k)
        if self.ramp_C_per_h:
            start = self.start_temperature_C if self.start_temperature_C is not None else 25.0
            return min(start + self.ramp_C_per_h * (t / 3600.0), self.gas_temperature_C) + T0_K
        return self.gas_temperature_C + T0_K

    def _specific_flux(self, t_gas_k: float, t_surface_k: float) -> float:
        """Flujo hacia el revestimiento [W/m2] para una temperatura de gas dada."""
        return (
            self.h_conv * (t_gas_k - t_surface_k)
            + self.eps_eff * SIGMA * (t_gas_k ** 4 - t_surface_k ** 4)
        )

    def gas_temperature(self, t_surface_k: float, t: float = 0.0) -> float:
        """Temperatura real de los gases [K].

        En modo potencia limitada resuelve el balance por biseccion. La funcion
        de balance es monotona decreciente en T_g y cambia de signo entre T_s y
        T_ad, de modo que la biseccion converge siempre.
        """
        if not self.power_limited:
            return self._setpoint_k(t)

        t_ad = self.adiabatic_flame_C + T0_K
        t_ref = self.ambient_C + T0_K
        setpoint = self._setpoint_k(t)          # techo de control del precalentador
        upper = min(t_ad, max(setpoint, t_surface_k + 1e-6))
        lower = max(min(t_surface_k, upper - 1e-6), t_ref)
        m_cp = self.burner_power_MW * 1.0e6 / (t_ad - t_ref)

        def balance(t_gas: float) -> float:
            return m_cp * (t_ad - t_gas) - self.heated_area * self._specific_flux(t_gas, t_surface_k)

        if balance(upper) >= 0.0:
            # El quemador tiene potencia de sobra: manda el setpoint de control.
            return upper
        if balance(lower) <= 0.0:
            return lower

        # Newton con salvaguarda de biseccion. El balance es monotono
        # decreciente y concavo en T_g, asi que Newton converge en 3-5 pasos;
        # la biseccion solo actua si un paso se sale del intervalo.
        eps_sigma = self.eps_eff * SIGMA
        t_gas = 0.5 * (lower + upper)
        for _ in range(40):
            f = balance(t_gas)
            if f > 0.0:
                lower = t_gas
            else:
                upper = t_gas
            df = -m_cp - self.heated_area * (self.h_conv + 4.0 * eps_sigma * t_gas ** 3)
            candidate = t_gas - f / df
            if not (lower < candidate < upper):
                candidate = 0.5 * (lower + upper)
            converged = abs(candidate - t_gas) < 1e-3
            t_gas = candidate
            if converged:
                break
        return t_gas

    def env_temperature(self, t: float = 0.0) -> float:
        if self.power_limited:
            return self.adiabatic_flame_C + T0_K
        return self._setpoint_k(t)

    def coefficient(self, t_surface_k: float, t: float = 0.0) -> float:
        if not self.power_limited:
            t_gas = self._setpoint_k(t)
            return self.h_conv + radiative_coefficient(t_surface_k, t_gas, self.eps_eff)

        t_gas = self.gas_temperature(t_surface_k, t)
        t_ad = self.adiabatic_flame_C + T0_K
        driving = t_ad - t_surface_k
        if driving <= 1.0:
            return 0.0
        return max(self._specific_flux(t_gas, t_surface_k), 0.0) / driving

    def thermal_efficiency(self, t_surface_k: float, t: float = 0.0) -> float:
        """Fraccion de la potencia del quemador que entra al revestimiento [-]."""
        if not self.power_limited:
            return float("nan")
        t_gas = self.gas_temperature(t_surface_k, t)
        absorbed = self.heated_area * self._specific_flux(t_gas, t_surface_k)
        return float(absorbed / (self.burner_power_MW * 1.0e6))

    def describe(self) -> str:
        if self.power_limited:
            txt = (
                f"Precalentador {self.burner_power_MW:.2f} MW (horno bien agitado, "
                f"llama adiabatica {self.adiabatic_flame_C:.0f} C, A={self.heated_area:.1f} m2, "
                f"h_conv={self.h_conv:.0f}, eps={self.eps_eff:.2f})"
            )
            if self.schedule_C or self.ramp_C_per_h:
                txt += f", techo de control {self.gas_temperature_C:.0f} C"
            return txt
        if self.schedule_C:
            prog = " -> ".join(f"{c:.0f}C@{m:.0f}min" for m, c in self.schedule_C)
            return f"Precalentador programado [{prog}] (potencia ilimitada), h_conv={self.h_conv:.0f}, eps={self.eps_eff:.2f}"
        txt = (
            f"Precalentador {self.gas_temperature_C:.0f} C (potencia ilimitada, limite superior), "
            f"h_conv={self.h_conv:.0f}, eps={self.eps_eff:.2f}"
        )
        if self.ramp_C_per_h:
            txt += f", rampa {self.ramp_C_per_h:.0f} C/h desde {self.start_temperature_C or 25:.0f} C"
        return txt


@dataclass
class AmbientShell(SurfaceBC):
    """Carcasa exterior: conveccion natural (o mixta) + radiacion al taller.

    Conveccion natural por Churchill-Chu para placa/cilindro vertical, o
    McAdams para placa horizontal caliente mirando hacia abajo (fondo de olla).
    Si `wind_speed` > 0 se anade conveccion forzada en placa plana y se toma el
    maximo entre natural y forzada (criterio conservador y habitual).
    """

    ambient_C: float = 35.0
    emissivity: float = 0.80
    characteristic_length: float = 3.5
    orientation: str = "vertical"
    wind_speed: float = 0.0
    h_conv_override: float | None = None
    name: str = "carcasa"

    def env_temperature(self, t: float = 0.0) -> float:
        return self.ambient_C + T0_K

    def natural_convection(self, t_surface_k: float) -> float:
        t_env = self.env_temperature()
        dt = abs(t_surface_k - t_env)
        if dt < 1e-6:
            return 0.0
        t_film = 0.5 * (t_surface_k + t_env)
        k_air, nu_air, pr = air_properties(t_film)
        beta = 1.0 / t_film
        length = max(self.characteristic_length, 1e-3)
        ra = GRAVITY * beta * dt * length ** 3 * pr / (nu_air ** 2)
        if self.orientation == "vertical":
            f_pr = (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (8.0 / 27.0)
            nu = (0.825 + 0.387 * ra ** (1.0 / 6.0) / f_pr) ** 2
        elif self.orientation == "horizontal_down":
            nu = 0.27 * ra ** 0.25
        elif self.orientation == "horizontal_up":
            nu = 0.15 * ra ** (1.0 / 3.0) if ra > 1e7 else 0.54 * ra ** 0.25
        else:
            raise ValueError(f"orientation desconocida: {self.orientation!r}")
        return float(nu * k_air / length)

    def forced_convection(self, t_surface_k: float) -> float:
        if self.wind_speed <= 0:
            return 0.0
        t_film = 0.5 * (t_surface_k + self.env_temperature())
        k_air, nu_air, pr = air_properties(t_film)
        length = max(self.characteristic_length, 1e-3)
        re = self.wind_speed * length / nu_air
        nu = 0.037 * re ** 0.8 * pr ** (1.0 / 3.0) if re > 5e5 else 0.664 * re ** 0.5 * pr ** (1.0 / 3.0)
        return float(nu * k_air / length)

    def coefficient(self, t_surface_k: float, t: float = 0.0) -> float:
        if self.h_conv_override is not None:
            h_conv = float(self.h_conv_override)
        else:
            h_conv = max(self.natural_convection(t_surface_k), self.forced_convection(t_surface_k))
        return h_conv + radiative_coefficient(t_surface_k, self.env_temperature(t), self.emissivity)

    def describe(self) -> str:
        txt = f"Carcasa al taller {self.ambient_C:.0f} C, eps={self.emissivity:.2f}, {self.orientation}"
        if self.wind_speed:
            txt += f", corriente {self.wind_speed:.1f} m/s"
        return txt
