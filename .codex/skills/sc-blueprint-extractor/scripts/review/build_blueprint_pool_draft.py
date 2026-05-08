from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys

from scdatatools.sc import StarCitizen

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import REPO_ROOT
from localization_tools import read_global_ini


DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"
DEFAULT_BLUEPRINTS_OVERLAY = REPO_ROOT / "source" / "shared" / "overlays" / "blueprints.ini"
DEFAULT_GLOBAL_EN = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_POOL_MAP_DRAFT.md"

POOL_RE = re.compile(rb"BP_MISSIONREWARD_[A-Za-z0-9_]+")
ITEM_REF_RE = re.compile(r"@(item_[A-Za-z0-9_.,-]+)@")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class MissionReward:
    title_key: str
    desc_key: str | None
    english_title: str
    desc_value: str | None
    item_refs: tuple[str, ...]
    candidate_pool: str | None
    candidate_score: int


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


def normalized_tokens(value: str) -> set[str]:
    parts = [part for part in NON_ALNUM_RE.split(value.lower()) if part]
    ignore = {
        "bp", "missionreward", "title", "desc", "reward", "mission", "fps",
        "all", "specific", "easy", "medium", "hard", "veryhard", "super",
        "local", "solar", "secondary", "primarysecondary", "planetary",
        "planetarysystem", "interstellar", "discoverplanetary", "intro",
    }
    return {part for part in parts if part not in ignore}


def family_name_from_title_key(title_key: str) -> str:
    key = replace_token(title_key, "title", "")
    key = replace_token(key, "desc", "")
    key = re.sub(r"_\d+$", "", key)
    key = re.sub(r"_0+\d+\b", "", key)
    return key.strip("_")


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


def choose_candidate_pool(title_key: str, pools: list[str]) -> tuple[str | None, int]:
    title_tokens = normalized_tokens(family_name_from_title_key(title_key))
    best_pool: str | None = None
    best_score = 0
    for pool in pools:
        overlap = len(title_tokens & normalized_tokens(pool))
        if overlap > best_score:
            best_pool = pool
            best_score = overlap
    return best_pool, best_score


def collect_mission_rewards(
    *,
    overlay_path: Path,
    english_map: dict[str, str],
    pools: list[str],
) -> list[MissionReward]:
    overlay_data = read_global_ini(overlay_path)
    overlay_map = overlay_data.mapping
    lower_to_real = {key.lower(): key for key in overlay_map}
    missions: list[MissionReward] = []
    seen_titles: set[str] = set()
    for key in overlay_map:
        if not has_token(key, "title"):
            continue
        key_lower = key.lower()
        if key_lower in seen_titles:
            continue
        seen_titles.add(key_lower)

        desc_guess = replace_token(key, "title", "desc")
        desc_key = lower_to_real.get(desc_guess.lower())
        desc_value = overlay_map.get(desc_key) if desc_key is not None else None
        item_refs = tuple(dict.fromkeys(ITEM_REF_RE.findall(desc_value or "")))
        candidate_pool, candidate_score = choose_candidate_pool(key, pools)
        missions.append(
            MissionReward(
                title_key=key,
                desc_key=desc_key,
                english_title=english_map.get(key, key),
                desc_value=desc_value,
                item_refs=item_refs,
                candidate_pool=candidate_pool,
                candidate_score=candidate_score,
            )
        )
    return missions


def reward_signature(item_refs: tuple[str, ...]) -> str:
    return "\x1f".join(item_refs)


def build_report(
    *,
    output_path: Path,
    overlay_path: Path,
    global_en_path: Path,
    sc_root: Path,
    dcb_member: str,
    pools: list[str],
    missions: list[MissionReward],
    english_map: dict[str, str],
) -> None:
    with_desc = [mission for mission in missions if mission.desc_key is not None]
    with_items = [mission for mission in with_desc if mission.item_refs]
    without_desc = [mission for mission in missions if mission.desc_key is None]

    signature_groups: dict[str, list[MissionReward]] = defaultdict(list)
    for mission in with_items:
        signature_groups[reward_signature(mission.item_refs)].append(mission)

    sorted_groups = sorted(
        signature_groups.values(),
        key=lambda group: (-len(group), group[0].english_title.lower(), group[0].title_key.lower()),
    )

    candidate_pool_counter = Counter(
        mission.candidate_pool for mission in with_items if mission.candidate_pool and mission.candidate_score > 0
    )

    pool_to_missions: dict[str, list[MissionReward]] = defaultdict(list)
    for mission in with_items:
        if mission.candidate_pool and mission.candidate_score > 0:
            pool_to_missions[mission.candidate_pool].append(mission)

    lines: list[str] = []
    lines.append("# Borrador de mapa de pools de blueprints")
    lines.append("")
    lines.append("Objetivo:")
    lines.append("- Agrupar misiones por recompensa visible real en `blueprints.ini`.")
    lines.append("- Cruzar cada grupo con pools `BP_MISSIONREWARD_*` detectadas en el parche.")
    lines.append("- Dejar una base util para refactorizar a un origen `pool -> items` y `mision -> pool`.")
    lines.append("")
    lines.append("Origenes usados:")
    lines.append(f"- Overlay compartido: `{overlay_path.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- `global.ini` ingles: `{global_en_path.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- Instalacion de Star Citizen: `{sc_root}`")
    lines.append(f"- DataForge detectado: `{dcb_member}`")
    lines.append("")
    lines.append("Resumen:")
    lines.append(f"- Misiones con `title`: {len(missions)}")
    lines.append(f"- Misiones con `desc`: {len(with_desc)}")
    lines.append(f"- Misiones con items visibles en `desc`: {len(with_items)}")
    lines.append(f"- Misiones sin `desc`: {len(without_desc)}")
    lines.append(f"- Pools detectadas en DataForge: {len(pools)}")
    lines.append(f"- Firmas exactas de recompensa visibles: {len(signature_groups)}")
    lines.append("")
    lines.append("## Pools detectadas")
    lines.append("")
    for pool in pools:
        assigned = len(pool_to_missions.get(pool, []))
        lines.append(f"- `{pool}` ({assigned} misiones candidatas)")
    lines.append("")
    lines.append("## Firmas exactas de recompensa")
    lines.append("")
    lines.append("Notas:")
    lines.append("- Una firma es la lista exacta y ordenada de `@item_...@` visible en un `desc`.")
    lines.append("- Si varias misiones comparten firma, son candidatas claras a reutilizar una misma `pool` en el origen.")
    lines.append("- La `pool` candidata sigue siendo heuristica mientras no resolvamos el enlace autoritativo desde `Game2.dcb`.")
    lines.append("")

    for index, group in enumerate(sorted_groups, start=1):
        signature_id = f"SIG-{index:02d}"
        first = group[0]
        pool_name = first.candidate_pool if first.candidate_score > 0 else None
        pool_votes = Counter(
            mission.candidate_pool for mission in group if mission.candidate_pool and mission.candidate_score > 0
        )

        lines.append(f"### {signature_id}")
        lines.append("")
        lines.append(f"- Misiones en el grupo: {len(group)}")
        lines.append(f"- `desc` representativa: `{first.desc_key}`")
        lines.append(
            "- Pool candidata dominante: "
            + (f"`{pool_name}`" if pool_name is not None else "sin coincidencia heuristica suficiente")
        )
        if pool_votes:
            votes_text = ", ".join(f"`{pool}` x{count}" for pool, count in pool_votes.most_common(3))
            lines.append(f"- Recuento de coincidencias heuristicas: {votes_text}")
        lines.append("")
        lines.append("| Mision | Clave `title` | Pool candidata | Score |")
        lines.append("|---|---|---|---|")
        for mission in sorted(group, key=lambda item: (item.english_title.lower(), item.title_key.lower())):
            lines.append(
                f"| `{mission.english_title}` | `{mission.title_key}` | "
                + (f"`{mission.candidate_pool}`" if mission.candidate_pool else "-")
                + f" | {mission.candidate_score} |"
            )
        lines.append("")
        lines.append("| Ref de item | Nombre ingles |")
        lines.append("|---|---|")
        for item_ref in first.item_refs:
            lines.append(f"| `{item_ref}` | `{english_map.get(item_ref, item_ref)}` |")
        lines.append("")

    if without_desc:
        lines.append("## Misiones sin `desc`")
        lines.append("")
        lines.append("| Mision | Clave `title` | `desc` esperada | Pool candidata | Score |")
        lines.append("|---|---|---|---|---|")
        for mission in sorted(without_desc, key=lambda item: (item.english_title.lower(), item.title_key.lower())):
            expected_desc = replace_token(mission.title_key, "title", "desc")
            lines.append(
                f"| `{mission.english_title}` | `{mission.title_key}` | `{expected_desc}` | "
                + (f"`{mission.candidate_pool}`" if mission.candidate_pool else "-")
                + f" | {mission.candidate_score} |"
            )
        lines.append("")

    lines.append("## Vista rapida por pool candidata")
    lines.append("")
    for pool, _count in candidate_pool_counter.most_common():
        lines.append(f"### {pool}")
        lines.append("")
        for mission in sorted(
            pool_to_missions[pool],
            key=lambda item: (item.english_title.lower(), item.title_key.lower()),
        ):
            lines.append(f"- `{mission.english_title}` -> `{mission.title_key}`")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agrupa misiones de blueprints por firma visible de recompensa y propone pools candidatas."
    )
    parser.add_argument("--overlay", default=str(DEFAULT_BLUEPRINTS_OVERLAY))
    parser.add_argument("--global-en", default=str(DEFAULT_GLOBAL_EN))
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    overlay_path = Path(args.overlay).expanduser().resolve()
    global_en_path = Path(args.global_en).expanduser().resolve()
    sc_root = Path(args.sc_root).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    english_map = read_global_ini(global_en_path).mapping
    dcb_member, pools = extract_pools(sc_root, cache_dir)
    missions = collect_mission_rewards(
        overlay_path=overlay_path,
        english_map=english_map,
        pools=pools,
    )
    build_report(
        output_path=output_path,
        overlay_path=overlay_path,
        global_en_path=global_en_path,
        sc_root=sc_root,
        dcb_member=dcb_member,
        pools=pools,
        missions=missions,
        english_map=english_map,
    )
    print(f"Informe generado: {output_path}")
    print(f"Misiones analizadas: {len(missions)}")
    print(f"Pools detectadas: {len(pools)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
