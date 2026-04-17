from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from scdatatools.sc import StarCitizen


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"
DEFAULT_BLUEPRINTS_EN = REPO_ROOT / "source" / "shared" / "overlays" / "blueprints.ini"
DEFAULT_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_REWARD_POOLS_DISCOVERY.md"

POOL_RE = re.compile(rb"BP_MISSIONREWARD_[A-Za-z0-9_]+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class OverlayMission:
    title_key: str
    desc_key: str | None


def read_ini_keys(path: Path) -> list[str]:
    keys: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw_line or raw_line.startswith((";", "#")) or "=" not in raw_line:
            continue
        keys.append(raw_line.split("=", 1)[0])
    return keys


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


def collect_overlay_missions(blueprints_path: Path) -> list[OverlayMission]:
    keys = read_ini_keys(blueprints_path)
    lower_keys = {key.lower(): key for key in keys}
    missions: list[OverlayMission] = []
    seen: set[str] = set()
    for key in keys:
        if not has_token(key, "title"):
            continue
        if key.lower() in seen:
            continue
        seen.add(key.lower())
        desc_key = replace_token(key, "title", "desc")
        missions.append(
            OverlayMission(
                title_key=key,
                desc_key=desc_key if desc_key.lower() in lower_keys else None,
            )
        )
    return missions


def normalized_tokens(value: str) -> set[str]:
    parts = [part for part in NON_ALNUM_RE.split(value.lower()) if part]
    ignore = {
        "bp",
        "missionreward",
        "title",
        "desc",
        "reward",
        "mission",
        "fps",
        "resource",
        "gathering",
        "eliminate",
        "specific",
        "all",
    }
    return {part for part in parts if part not in ignore}


def family_name_from_title_key(title_key: str) -> str:
    key = replace_token(title_key, "title", "")
    key = replace_token(key, "desc", "")
    key = re.sub(r"_\d+$", "", key)
    key = re.sub(r"_0+\d+\b", "", key)
    key = key.strip("_")
    return key


def extract_pools(sc_root: Path, cache_dir: Path) -> tuple[str, list[str]]:
    sc = StarCitizen(sc_root, cache_dir=cache_dir)
    for member in ("Data/Game.dcb", "Data/Game2.dcb"):
        try:
            raw = sc.p4k.getinfo(member).open("rb").read()
            pools = sorted({match.group(0).decode("ascii") for match in POOL_RE.finditer(raw)})
            return member, pools
        except KeyError:
            continue
    raise FileNotFoundError("No se encontro Data/Game.dcb ni Data/Game2.dcb en la instalacion.")


def build_pool_matches(pools: list[str], missions: list[OverlayMission]) -> dict[str, list[OverlayMission]]:
    mission_index: list[tuple[OverlayMission, set[str]]] = []
    for mission in missions:
        family = family_name_from_title_key(mission.title_key)
        mission_index.append((mission, normalized_tokens(family)))

    matches: dict[str, list[OverlayMission]] = {}
    for pool in pools:
        pool_tokens = normalized_tokens(pool)
        candidates: list[tuple[int, OverlayMission]] = []
        for mission, mission_tokens in mission_index:
            overlap = len(pool_tokens & mission_tokens)
            if overlap <= 0:
                continue
            candidates.append((overlap, mission))
        candidates.sort(key=lambda item: (-item[0], item[1].title_key.lower()))
        matches[pool] = [mission for _, mission in candidates[:12]]
    return matches


def build_report(
    *,
    output_path: Path,
    blueprints_path: Path,
    sc_root: Path,
    dcb_member: str,
    missions: list[OverlayMission],
    pools: list[str],
    matches: dict[str, list[OverlayMission]],
) -> None:
    missions_with_desc = sum(1 for mission in missions if mission.desc_key is not None)
    lines: list[str] = []
    lines.append("# Descubrimiento de pools de recompensas de blueprints")
    lines.append("")
    lines.append("Objetivo:")
    lines.append("- Detectar pools `BP_MISSIONREWARD_*` en el parche instalado.")
    lines.append("- Inventariar las misiones del overlay `blueprints.ini` con y sin `desc`.")
    lines.append("- Estimar coincidencias por nombre para preparar un posible refactor a pools reutilizables.")
    lines.append("")
    lines.append("Origenes usados:")
    lines.append(f"- Overlay compartido: `{blueprints_path.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- Instalacion de Star Citizen: `{sc_root}`")
    lines.append(f"- DataForge detectado: `{dcb_member}`")
    lines.append("")
    lines.append("Resumen:")
    lines.append(f"- Misiones `title` detectadas en overlay: {len(missions)}")
    lines.append(f"- Misiones con `desc` presente en overlay: {missions_with_desc}")
    lines.append(f"- Pools `BP_MISSIONREWARD_*` detectados en DataForge: {len(pools)}")
    lines.append("")
    lines.append("## Pools detectados")
    lines.append("")
    for pool in pools:
        lines.append(f"- `{pool}`")
    lines.append("")
    lines.append("## Misiones del overlay")
    lines.append("")
    lines.append("| Clave `title` | `desc` presente |")
    lines.append("|---|---|")
    for mission in missions:
        lines.append(f"| `{mission.title_key}` | `{'si' if mission.desc_key else 'no'}` |")
    lines.append("")
    lines.append("## Coincidencias heuristicas pool -> misiones")
    lines.append("")
    lines.append("Notas:")
    lines.append("- Esto no es un enlace autoritativo todavia; solo usa similitud de tokens en nombres.")
    lines.append("- Sirve para ver si compensa introducir un archivo `pools` y reducir mantenimiento manual en `blueprints.ini`.")
    lines.append("")
    for pool in pools:
        lines.append(f"### {pool}")
        candidates = matches.get(pool, [])
        if not candidates:
            lines.append("")
            lines.append("Sin coincidencias heuristicas en el overlay actual.")
            lines.append("")
            continue
        lines.append("")
        for mission in candidates:
            lines.append(
                f"- `{mission.title_key}`"
                + (f" -> `{mission.desc_key}`" if mission.desc_key else " -> sin `desc`")
            )
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descubre pools BP_MISSIONREWARD_* y los cruza heurísticamente con el overlay blueprints."
    )
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--blueprints-en", default=str(DEFAULT_BLUEPRINTS_EN))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    sc_root = Path(args.sc_root).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    blueprints_path = Path(args.blueprints_en).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    missions = collect_overlay_missions(blueprints_path)
    dcb_member, pools = extract_pools(sc_root, cache_dir)
    matches = build_pool_matches(pools, missions)
    build_report(
        output_path=output_path,
        blueprints_path=blueprints_path,
        sc_root=sc_root,
        dcb_member=dcb_member,
        missions=missions,
        pools=pools,
        matches=matches,
    )

    print(f"Informe generado: {output_path}")
    print(f"Pools detectados: {len(pools)}")
    print(f"Misiones overlay: {len(missions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
