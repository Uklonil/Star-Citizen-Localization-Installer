from __future__ import annotations

import argparse
from pathlib import Path

from scdatatools.sc import StarCitizen

DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen")
DEFAULT_SC_CHANNEL = "LIVE"
REPO_ROOT = Path(__file__).resolve().parent.parent


def find_english_global_ini(sc: StarCitizen):
    matches = list(sc.p4k.search("Data/Localization/english/global.ini"))
    if not matches:
        raise FileNotFoundError("No se encontro Data/Localization/english/global.ini en Data.p4k")
    return matches[0]


def default_live_path() -> Path:
    return (DEFAULT_SC_ROOT / DEFAULT_SC_CHANNEL).resolve()


def default_output_path() -> Path:
    return REPO_ROOT / "input" / "current" / "global.ini"


def default_cache_dir() -> Path:
    return REPO_ROOT / ".scdt-cache"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrae el global.ini ingles directamente desde una instalacion de Star Citizen o un Data.p4k."
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=str(default_live_path()),
        help="Ruta a la carpeta LIVE/PTU de Star Citizen o al archivo Data.p4k",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(default_output_path()),
        help="Ruta de salida para el global.ini extraido",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(default_cache_dir()),
        help="Directorio de cache para scdatatools",
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()

    sc = StarCitizen(source, cache_dir=cache_dir)
    english_info = find_english_global_ini(sc)

    output.parent.mkdir(parents=True, exist_ok=True)
    with sc.p4k.open(english_info) as src, output.open("wb") as dst:
        dst.write(src.read())

    print(f"Extraido: {english_info.filename}")
    print(f"Origen: {source}")
    print(f"Salida: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
