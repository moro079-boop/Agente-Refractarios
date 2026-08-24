"""Interfaz de linea de comandos de `ladle-thermal`.

    ladle-thermal describe config/studies/precalentamiento_base.yaml
    ladle-thermal cool     config/studies/precalentamiento_base.yaml
    ladle-thermal run      config/studies/precalentamiento_base.yaml --out results/base
    ladle-thermal preheat  config/studies/precalentamiento_base.yaml --scenario sin_tapa --after 120
    ladle-thermal validate
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .cycle import Segment, run_segments
from .preheat import required_preheat_time
from .scenarios import StudyConfig, load_study
from .study import build_preheat_map


def _out_dir(args, config: StudyConfig) -> Path:
    path = Path(args.out) if args.out else Path("results") / config.name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_cooling(config: StudyConfig, initial_state, max_minutes: float):
    from .study import CoolingScenario

    scenarios = config.cooling_scenarios()
    histories = {}
    for sc in scenarios:
        histories[sc.name] = run_segments(
            config.mesh, config.materials,
            [Segment(f"enfriamiento_{sc.name}", max_minutes * 60.0, sc.bc)],
            initial_state, config.shell_bc(), config.options(),
        )
    return scenarios, histories


def cmd_describe(args) -> int:
    config = load_study(args.study)
    print(config.describe())
    return 0


def cmd_cool(args) -> int:
    from .report import plot_cooling_curves, plot_profiles

    config = load_study(args.study)
    out = _out_dir(args, config)
    print(f"[1/3] Estado inicial ({config.raw.get('initial_state', {}).get('mode', 'cyclic')})...", flush=True)
    state, state_desc = config.initial_state(verbose=True)
    print(f"      {state_desc}")

    max_min = args.max_minutes or max(config.cooling_times_min())
    print(f"[2/3] Enfriamiento sin aporte energetico hasta {max_min:.0f} min...", flush=True)
    scenarios, histories = _run_cooling(config, state, max_min)

    marks = [m for m in (0, 15, 30, 60, 90, 120, 180, 240, 360, 480) if m <= max_min]
    print(f"\n{'Escenario':<22s}" + "".join(f"{m:>8d}m" for m in marks))
    for name, h in histories.items():
        row = "".join(f"{np.interp(m*60.0, h.times, h.hot_face_C):>9.0f}" for m in marks)
        print(f"{name:<22s}{row}")
    print("\n(temperaturas de CARA CALIENTE en C)")

    print("\n[3/3] Figuras y CSV...", flush=True)
    fig1 = plot_cooling_curves(histories, out / "enfriamiento.png",
                               target_C=config.criterion().hot_face_C)
    fig2 = plot_profiles(histories[scenarios[0].name], out / "perfiles_enfriamiento.png",
                         title=f"Perfil en el espesor durante el enfriamiento ({scenarios[0].name})")
    for name, h in histories.items():
        h.to_csv(out / f"enfriamiento_{name}.csv", include_profile=args.profiles)
    print(f"      {fig1}\n      {fig2}\n      CSV en {out}")
    return 0


def cmd_preheat(args) -> int:
    config = load_study(args.study)
    state, state_desc = config.initial_state(verbose=True)
    scenarios = {sc.name: sc for sc in config.cooling_scenarios()}
    if args.scenario not in scenarios:
        print(f"Escenario '{args.scenario}' no existe. Disponibles: {sorted(scenarios)}", file=sys.stderr)
        return 2

    if args.after > 0:
        cooling = run_segments(
            config.mesh, config.materials,
            [Segment("enfriamiento", args.after * 60.0, scenarios[args.scenario].bc)],
            state, config.shell_bc(), config.options(),
        )
        state = cooling.final_state
        print(f"Tras {args.after:.0f} min en '{args.scenario}': cara caliente "
              f"{cooling.hot_face_C[-1]:.0f} C, carcasa {cooling.shell_C[-1]:.0f} C")

    result = required_preheat_time(
        config.mesh, config.materials, state, config.preheater(), config.criterion(),
        max_time=float(config.raw.get("max_preheat_h", 14.0)) * 3600.0,
        bc_cold=config.shell_bc(), options=config.options(),
    )
    print(f"\nEstado de partida: {state_desc}")
    print(result.summary())
    if args.out:
        out = _out_dir(args, config)
        result.history.to_csv(out / f"precalentamiento_{args.scenario}_{args.after:.0f}min.csv")
        print(f"CSV en {out}")
    return 0 if result.criterion_met else 1


def cmd_run(args) -> int:
    from .report import (
        plot_cooling_curves,
        plot_preheat_curves,
        plot_preheat_map,
        plot_profiles,
        write_map_csv,
        write_report,
    )

    config = load_study(args.study)
    out = _out_dir(args, config)
    started = datetime.now(timezone.utc)

    print(f"Estudio '{config.name}' -> {out}")
    print("[1/4] Estado termico de partida...", flush=True)
    state, state_desc = config.initial_state(verbose=True)
    print(f"      {state_desc}")

    print("[2/4] Mapa espera -> precalentador...", flush=True)
    pmap = build_preheat_map(
        config.mesh, config.materials, state,
        config.cooling_scenarios(), config.cooling_times_min(),
        config.preheater(), config.criterion(),
        bc_cold=config.shell_bc(), options=config.options(),
        max_preheat_h=float(config.raw.get("max_preheat_h", 14.0)),
        progress=True,
    )
    pmap.initial_state_description = state_desc

    print("[3/4] Figuras...", flush=True)
    figures = [
        ("Enfriamiento de la olla vacia", plot_cooling_curves(
            pmap.cooling_histories, out / "enfriamiento.png", config.criterion().hot_face_C)),
        ("Perfil de temperatura en el espesor", plot_profiles(
            pmap.cooling_histories[pmap.scenarios[0].name], out / "perfiles.png",
            title=f"Perfil durante el enfriamiento ({pmap.scenarios[0].name})")),
        ("Precalentamiento requerido", plot_preheat_map(pmap, out / "mapa_precalentamiento.png")),
        ("Curvas de precalentamiento", plot_preheat_curves(pmap, out / "curvas_precalentamiento.png")),
    ]

    print("[4/4] Reporte...", flush=True)
    write_map_csv(pmap, out / "mapa_precalentamiento.csv")
    context = {
        "Olla": f"{config.ladle.name} (seccion '{config.section.name}', {config.mesh.n_cells} celdas)",
        "Espesores": ", ".join(
            f"{l.name} {l.thickness*1000:.0f} mm ({l.material})" for l in config.section.layers),
        "Estado de partida": state_desc,
        "Precalentador": pmap.burner_description,
        "Criterio": config.criterion().describe(),
        "Ambiente": f"{config.ambient_C:.0f} C",
        "Archivo de estudio": str(config.path),
        "Duracion del calculo": f"{(datetime.now(timezone.utc)-started).total_seconds():.0f} s",
    }
    report = write_report(
        pmap, out / "REPORTE.md",
        title=f"Tiempo de precalentamiento requerido - {config.name}",
        context=context, figures=figures,
    )
    print("\n" + pmap.to_markdown())
    print(f"\nReporte: {report}")
    return 0


def cmd_validate(args) -> int:
    from .validation import run_all

    results = run_all(verbose=True)
    failed = [r for r in results if not r.passed]
    print(f"\n{len(results)-len(failed)}/{len(results)} verificaciones superadas")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ladle-thermal",
        description="Modelo termico 1D radial de ollas de acero: enfriamiento y precalentamiento.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("describe", help="Muestra la configuracion de un estudio")
    p.add_argument("study")
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("cool", help="Solo curvas de enfriamiento sin aporte energetico")
    p.add_argument("study")
    p.add_argument("--out", default=None)
    p.add_argument("--max-minutes", type=float, default=None, dest="max_minutes")
    p.add_argument("--profiles", action="store_true", help="Incluye el perfil completo en el CSV")
    p.set_defaults(func=cmd_cool)

    p = sub.add_parser("preheat", help="Tiempo de precalentador tras una espera dada")
    p.add_argument("study")
    p.add_argument("--scenario", default="sin_tapa")
    p.add_argument("--after", type=float, default=0.0, help="Minutos de espera vacia previos")
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_preheat)

    p = sub.add_parser("run", help="Estudio completo con reporte y figuras")
    p.add_argument("study")
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("validate", help="Verificaciones del solver contra soluciones analiticas")
    p.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
