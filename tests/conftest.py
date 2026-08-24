import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402

from ladle_thermal.geometry import Layer, Section  # noqa: E402
from ladle_thermal.materials import load_materials  # noqa: E402
from ladle_thermal.mesh import build_mesh  # noqa: E402


@pytest.fixture(scope="session")
def library():
    return load_materials()


@pytest.fixture(scope="session")
def material_names(library):
    return tuple(library.names())


@pytest.fixture(scope="session")
def materials(library, material_names):
    return [library[n] for n in material_names]


@pytest.fixture(scope="session")
def wall_section():
    return Section(
        name="wall",
        layers=(
            Layer("trabajo", "alumina_spinel_castable", 0.160, 16, 1.08),
            Layer("seguridad", "high_alumina_brick_70", 0.070, 6),
            Layer("aislante", "microporous_board", 0.015, 3),
            Layer("carcasa", "carbon_steel_shell", 0.030, 3),
        ),
        geometry="cylindrical",
        inner_radius=1.60,
        height=3.40,
    )


@pytest.fixture(scope="session")
def wall_mesh(wall_section, material_names):
    return build_mesh(wall_section, material_names)


@pytest.fixture(scope="session")
def repo_root():
    return ROOT
