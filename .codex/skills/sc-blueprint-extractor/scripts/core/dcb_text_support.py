from __future__ import annotations

from pathlib import Path
import sys

from scdatatools.sc import StarCitizen


CORE_SCRIPTS = Path(__file__).resolve().parent
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import find_datacore_member


def load_raw_dcb(sc_root: Path, cache_dir: Path) -> tuple[str, bytes]:
    sc = StarCitizen(sc_root, cache_dir=cache_dir)
    dcb_member = find_datacore_member(sc)
    if dcb_member is None:
        raise FileNotFoundError("No se encontro Data/Game.dcb ni Data/Game2.dcb en la instalacion.")
    return dcb_member, sc.p4k.getinfo(dcb_member).open("rb").read()


def split_strings_with_offsets(raw: bytes) -> list[tuple[int, str]]:
    strings: list[tuple[int, str]] = []
    offset = 0
    for part in raw.split(b"\x00"):
        if part:
            try:
                value = part.decode("utf-8")
            except UnicodeDecodeError:
                value = None
            if value:
                strings.append((offset, value))
        offset += len(part) + 1
    return strings


def build_title_index(strings: list[tuple[int, str]]) -> dict[str, int]:
    index: dict[str, int] = {}
    for offset, value in strings:
        if value.startswith("@") and value not in index:
            index[value[1:]] = offset
    return index
