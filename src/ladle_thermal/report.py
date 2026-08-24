"""Generacion de graficas y reportes en Markdown."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .cycle import History  # noqa: E402
from .study import PreheatMap  # noqa: E402

# Paleta sobria y con contraste suficiente en impresion b/n.
_COLORS = ["#1b4965", "#c1666b", "#5b8c5a", "#d4a373", "#6b4e71", "#3d5a80"]
_GRID = {"color": "#cccccc", "linewidth": 0.6, "alpha": 0.7}


def _style(ax, xlabel: str, ylabel: str, title: str = "") -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontsize=11)
    ax.grid(True, **_GRID)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def plot_cooling_curves(
    histories: dict[str, History],
    path: str | Path,
    target_C: float | None = 1100.0,
    title: str = "Enfriamiento de la olla vacia sin aporte energetico",
) -> Path:
    """Cara caliente y carcasa frente al tiempo para varios escenarios."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7.5), sharex=True)
    for i, (name, h) in enumerate(histories.items()):
        c = _COLORS[i % len(_COLORS)]
        ax1.plot(h.times_min, h.hot_face_C, color=c, lw=1.8, label=name)
        ax2.plot(h.times_min, h.shell_C, color=c, lw=1.8, label=name)
    if target_C is not None:
        ax1.axhline(target_C, color="#b00020", ls="--", lw=1.2)
        ax1.annotate(f"{target_C:.0f} C (criterio de colada)", xy=(0.98, target_C),
                     xycoords=("axes fraction", "data"), ha="right", va="bottom",
                     fontsize=8.5, color="#b00020")
    _style(ax1, "", "Cara caliente del refractario [C]", title)
    _style(ax2, "Tiempo de espera [min]", "Carcasa exterior [C]")
    ax1.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_profiles(
    history: History,
    path: str | Path,
    times_min: list[float] | None = None,
    title: str = "Perfil de temperatura en el espesor",
) -> Path:
    """Perfil T(x) en varios instantes, con las interfaces de capa marcadas."""
    times_min = times_min or [0, 15, 30, 60, 120, 240]
    mesh = history.mesh
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for i, tm in enumerate(times_min):
        t = min(tm * 60.0, history.times[-1])
        state = history.state_at(t) - 273.15
        ax.plot(mesh.depth_node * 1000.0, state, color=_COLORS[i % len(_COLORS)],
                lw=1.8, label=f"{t/60.0:.0f} min")
    # Interfaces de capa a partir de las caras de la malla
    boundaries = []
    for li in range(len(mesh.layer_names) - 1):
        last = np.max(np.where(mesh.layer_index == li)[0])
        boundaries.append(float(mesh.x_face[last + 1] - mesh.x_face[0]) * 1000.0)
    for b, name in zip(boundaries, mesh.layer_names[:-1]):
        ax.axvline(b, color="#888888", ls=":", lw=1.0)
        ax.annotate(name, xy=(b, ax.get_ylim()[1]), rotation=90, fontsize=7.5,
                    ha="right", va="top", color="#555555")
    _style(ax, "Profundidad desde la cara caliente [mm]", "Temperatura [C]", title)
    ax.legend(frameon=False, fontsize=9, title="tiempo", title_fontsize=9)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_preheat_map(pmap: PreheatMap, path: str | Path) -> Path:
    """Minutos de precalentador frente a tiempo de espera, una curva por escenario."""
    fig, ax = plt.subplots(figsize=(9, 5.4))
    matrix = pmap.matrix()
    for i, sc in enumerate(pmap.scenarios):
        ax.plot(pmap.cooling_times_min, matrix[i], marker="o", ms=5,
                color=_COLORS[i % len(_COLORS)], lw=1.8, label=sc.name)
    _style(ax, "Tiempo de espera de la olla vacia [min]",
           "Precalentamiento requerido [min]",
           f"Precalentador necesario para cumplir: {pmap.criterion.describe()}")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_preheat_curves(pmap: PreheatMap, path: str | Path, scenario: str | None = None) -> Path:
    """Evolucion de la cara caliente durante el precalentamiento."""
    scenario = scenario or pmap.scenarios[0].name
    fig, ax = plt.subplots(figsize=(9, 5.4))
    for i, ct in enumerate(pmap.cooling_times_min):
        key = (scenario, ct)
        if key not in pmap.preheat_histories:
            continue
        h = pmap.preheat_histories[key]
        ax.plot(h.times_min, h.hot_face_C, color=_COLORS[i % len(_COLORS)], lw=1.7,
                label=f"tras {ct:.0f} min de espera")
    ax.axhline(pmap.criterion.hot_face_C, color="#b00020", ls="--", lw=1.2)
    _style(ax, "Tiempo en el precalentador [min]", "Cara caliente [C]",
           f"Precalentamiento - escenario '{scenario}'")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def write_map_csv(pmap: PreheatMap, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(pmap.to_csv_rows())
    return path


def write_report(
    pmap: PreheatMap,
    path: str | Path,
    title: str,
    context: dict[str, str],
    figures: list[tuple[str, Path]],
    caveats: list[str] | None = None,
) -> Path:
    """Escribe el reporte en Markdown del estudio."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [f"# {title}", "", f"_Generado {stamp} por `ladle-thermal`._", ""]

    lines += ["## Configuracion de la corrida", ""]
    for key, value in context.items():
        lines.append(f"- **{key}**: {value}")
    lines += ["", "## Resultado: precalentamiento requerido", "", pmap.to_markdown(), ""]

    matrix = pmap.matrix()
    if np.isfinite(matrix).any():
        lines += ["### Lectura rapida", ""]
        for i, sc in enumerate(pmap.scenarios):
            row = matrix[i]
            finite = row[np.isfinite(row)]
            if finite.size:
                lines.append(
                    f"- **{sc.name}**: entre {finite.min():.0f} y {finite.max():.0f} min de precalentador "
                    f"segun la espera ({pmap.cooling_times_min[0]:.0f}-{pmap.cooling_times_min[-1]:.0f} min)."
                )
        lines.append("")

    if figures:
        lines += ["## Figuras", ""]
        for caption, fig_path in figures:
            rel = Path(fig_path).name
            lines += [f"**{caption}**", "", f"![{caption}]({rel})", ""]

    lines += ["## Limitaciones de esta corrida", ""]
    default_caveats = [
        "El modelo es 1D radial: no representa gradientes axiales, la linea de escoria, "
        "la zona de impacto ni el fondo/buza. Los tiempos son de la PARED.",
        "Las propiedades de los materiales son valores tipicos de literatura, no fichas "
        "tecnicas del refractario instalado. Ver `docs/propiedades_materiales.md`.",
        "El factor de intercambio radiativo de la olla vacia y `eps_eff` del precalentador "
        "son los dos parametros que mas mueven el resultado y ambos requieren calibracion "
        "contra una curva medida (termopar de carcasa o pirometro de cara caliente).",
        "No se modela el desgaste ni el adelgazamiento del revestimiento: una olla al final "
        "de campana tiene menos espesor de trabajo y se comporta distinto.",
    ]
    for caveat in (caveats or []) + default_caveats:
        lines.append(f"- {caveat}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
