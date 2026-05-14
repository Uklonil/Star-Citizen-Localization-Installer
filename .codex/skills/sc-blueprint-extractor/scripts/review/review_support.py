from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from scdatatools.sc import StarCitizen
except ModuleNotFoundError:  # pragma: no cover - optional at runtime
    StarCitizen = None


CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import REPO_ROOT, find_datacore_member

REPO_SCRIPTS = REPO_ROOT / "scripts"
if str(REPO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REPO_SCRIPTS))

from localization_tools import read_global_ini


DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"
DEFAULT_EXTRACTED_GAME2 = REPO_ROOT / "data" / "starcitizen" / "extracts" / "current" / "game2" / "Game2.dcb"

POOL_RE = re.compile(rb"BP_MISSIONREWARD_[A-Za-z0-9_]+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def read_ini_map(path: Path) -> dict[str, str]:
    return read_global_ini(path).mapping


def read_ini_keys(path: Path) -> list[str]:
    return [entry.key for entry in read_global_ini(path).entries]


def replace_token(value: str, source_token: str, target_token: str) -> str:
    parts = value.split("_")
    replaced = False
    for index, part in enumerate(parts):
        if part.lower() == source_token.lower():
            parts[index] = target_token
            replaced = True
            break
    return "_".join(parts) if replaced else value


def has_token(value: str, token: str) -> bool:
    return any(part.lower() == token.lower() for part in value.split("_"))


def normalized_tokens(value: str, *, ignore: set[str]) -> set[str]:
    parts = [part for part in NON_ALNUM_RE.split(value.lower()) if part]
    return {part for part in parts if part not in ignore}


def family_name_from_title_key(title_key: str) -> str:
    key = replace_token(title_key, "title", "")
    key = replace_token(key, "desc", "")
    key = replace_token(key, "description", "")
    key = re.sub(r"_\d+$", "", key)
    key = re.sub(r"_0+\d+\b", "", key)
    return key.strip("_")


def load_raw_datacore(sc_root: Path, cache_dir: Path) -> tuple[str, bytes]:
    if DEFAULT_EXTRACTED_GAME2.exists():
        return str(DEFAULT_EXTRACTED_GAME2), DEFAULT_EXTRACTED_GAME2.read_bytes()

    if StarCitizen is None:
        raise ModuleNotFoundError(
            "scdatatools no esta disponible y no existe un Game2.dcb extraido en "
            f"{DEFAULT_EXTRACTED_GAME2}."
        )

    sc = StarCitizen(sc_root, cache_dir=cache_dir)
    member = find_datacore_member(sc)
    if member is None:
        raise FileNotFoundError("No se encontro Data/Game.dcb ni Data/Game2.dcb en la instalacion.")
    return member, sc.p4k.getinfo(member).open("rb").read()


def extract_pools(sc_root: Path, cache_dir: Path) -> tuple[str, list[str]]:
    member, raw = load_raw_datacore(sc_root, cache_dir)
    pools = sorted({match.group(0).decode("ascii") for match in POOL_RE.finditer(raw)})
    return member, pools
