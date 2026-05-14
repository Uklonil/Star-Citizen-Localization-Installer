from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scdatatools.sc import StarCitizen
else:
    StarCitizen = Any


REPO_ROOT = Path(__file__).resolve().parents[5]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def find_datacore_member(sc: StarCitizen) -> str | None:
    for candidate in ("Data/Game.dcb", "Data/Game2.dcb"):
        try:
            sc.p4k.getinfo(candidate)
            return candidate
        except KeyError:
            continue
    return None
