from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from review_support import (
    DEFAULT_CACHE_DIR,
    DEFAULT_SC_ROOT,
    REPO_ROOT,
    extract_pools,
    family_name_from_title_key,
    has_token,
    normalized_tokens,
    read_ini_keys,
    replace_token,
)
from localization_tools import read_global_ini


DEFAULT_BLUEPRINTS_OVERLAY = REPO_ROOT / "source" / "shared" / "overlays" / "blueprints.ini"
DEFAULT_GLOBAL_EN = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_DISCOVERY_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_REWARD_POOLS_DISCOVERY.md"
DEFAULT_DRAFT_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_POOL_MAP_DRAFT.md"

DISCOVERY_IGNORE_TOKENS = {
    "bp", "missionreward", "title", "desc", "reward", "mission",
    "fps", "resource", "gathering", "eliminate", "specific", "all",
}
DRAFT_IGNORE_TOKENS = {
    "bp", "missionreward", "title", "desc", "reward", "mission", "fps",
    "all", "specific", "easy", "medium", "hard", "veryhard", "super",
    "local", "solar", "secondary", "primarysecondary", "planetary",
    "planetarysystem", "interstellar", "discoverplanetary", "intro",
}
ITEM_REF_RE = re.compile(r"@(item_[A-Za-z0-9_.,-]+)@")


@dataclass(frozen=True)
class OverlayMission:
    title_key: str
    desc_key: str | None


@dataclass(frozen=True)
class MissionReward:
    title_key: str
    desc_key: str | None
    english_title: str
    desc_value: str | None
    item_refs: tuple[str, ...]
    candidate_pool: str | None
    candidate_score: int


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


def build_pool_matches(pools: list[str], missions: list[OverlayMission]) -> dict[str, list[OverlayMission]]:
    mission_index: list[tuple[OverlayMission, set[str]]] = []
    for mission in missions:
        family = family_name_from_title_key(mission.title_key)
        mission_index.append((mission, normalized_tokens(family, ignore=DISCOVERY_IGNORE_TOKENS)))

    matches: dict[str, list[OverlayMission]] = {}
    for pool in pools:
        pool_tokens = normalized_tokens(pool, ignore=DISCOVERY_IGNORE_TOKENS)
        candidates: list[tuple[int, OverlayMission]] = []
        for mission, mission_tokens in mission_index:
            overlap = len(pool_tokens & mission_tokens)
            if overlap <= 0:
                continue
            candidates.append((overlap, mission))
        candidates.sort(key=lambda item: (-item[0], item[1].title_key.lower()))
        matches[pool] = [mission for _, mission in candidates[:12]]
    return matches


def build_discovery_report(
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


def choose_candidate_pool(title_key: str, pools: list[str]) -> tuple[str | None, int]:
    title_tokens = normalized_tokens(family_name_from_title_key(title_key), ignore=DRAFT_IGNORE_TOKENS)
    best_pool: str | None = None
    best_score = 0
    for pool in pools:
        overlap = len(title_tokens & normalized_tokens(pool, ignore=DRAFT_IGNORE_TOKENS))
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


def build_draft_report(
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


def run_discovery(
    *,
    sc_root: Path,
    cache_dir: Path,
    blueprints_path: Path,
    output_path: Path,
) -> tuple[list[OverlayMission], str, list[str]]:
    missions = collect_overlay_missions(blueprints_path)
    dcb_member, pools = extract_pools(sc_root, cache_dir)
    matches = build_pool_matches(pools, missions)
    build_discovery_report(
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
    return missions, dcb_member, pools


def run_draft(
    *,
    sc_root: Path,
    cache_dir: Path,
    overlay_path: Path,
    global_en_path: Path,
    output_path: Path,
    cached_pools: tuple[str, list[str]] | None = None,
) -> list[MissionReward]:
    english_map = read_global_ini(global_en_path).mapping
    if cached_pools is None:
        dcb_member, pools = extract_pools(sc_root, cache_dir)
    else:
        dcb_member, pools = cached_pools
    missions = collect_mission_rewards(
        overlay_path=overlay_path,
        english_map=english_map,
        pools=pools,
    )
    build_draft_report(
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
    return missions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Consolida descubrimiento de pools y borrador de mapa de pools de blueprints."
    )
    parser.add_argument("--mode", choices=("discover", "draft", "both"), default="both")
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--blueprints-en", default=str(DEFAULT_BLUEPRINTS_OVERLAY))
    parser.add_argument("--overlay", default=str(DEFAULT_BLUEPRINTS_OVERLAY))
    parser.add_argument("--global-en", default=str(DEFAULT_GLOBAL_EN))
    parser.add_argument("--output", default=str(DEFAULT_DISCOVERY_OUTPUT))
    parser.add_argument("--draft-output", default=str(DEFAULT_DRAFT_OUTPUT))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sc_root = Path(args.sc_root).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    blueprints_path = Path(args.blueprints_en).expanduser().resolve()
    overlay_path = Path(args.overlay).expanduser().resolve()
    global_en_path = Path(args.global_en).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    draft_output = Path(args.draft_output).expanduser().resolve()

    cached_pools: tuple[str, list[str]] | None = None
    if args.mode in {"discover", "both"}:
        _missions, dcb_member, pools = run_discovery(
            sc_root=sc_root,
            cache_dir=cache_dir,
            blueprints_path=blueprints_path,
            output_path=output_path,
        )
        cached_pools = (dcb_member, pools)

    if args.mode in {"draft", "both"}:
        run_draft(
            sc_root=sc_root,
            cache_dir=cache_dir,
            overlay_path=overlay_path,
            global_en_path=global_en_path,
            output_path=draft_output,
            cached_pools=cached_pools,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
