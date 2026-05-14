from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys

from scdatatools.sc import StarCitizen

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import REPO_ROOT
from localization_tools import read_global_ini
from blueprint_pool_source import default_blueprint_source_paths


DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"
DEFAULT_OVERLAY = REPO_ROOT / "source" / "shared" / "overlays" / "blueprints.ini"
DEFAULT_GLOBAL_EN = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_DISCOVERY_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_POOLS_DISCOVERY.json"

POOL_RE = re.compile(rb"BP_MISSIONREWARD_[A-Za-z0-9_]+")
ITEM_REF_RE = re.compile(r"@(item_[A-Za-z0-9_.,-]+)@")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
ITEM_LINE_RE = re.compile(r"^- @(item_[A-Za-z0-9_.,-]+)@$")


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


def family_name_from_title_key(title_key: str) -> str:
    key = replace_token(title_key, "title", "")
    key = replace_token(key, "desc", "")
    key = re.sub(r"_\d+$", "", key)
    key = re.sub(r"_0+\d+\b", "", key)
    return key.strip("_")


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
        "all",
        "specific",
        "easy",
        "medium",
        "hard",
        "veryhard",
        "super",
        "local",
        "solar",
        "secondary",
        "primarysecondary",
        "planetary",
        "planetarysystem",
        "interstellar",
        "discoverplanetary",
        "intro",
    }
    return {part for part in parts if part not in ignore}


def extract_pools(sc_root: Path, cache_dir: Path) -> list[str]:
    sc = StarCitizen(sc_root, cache_dir=cache_dir)
    for member in ("Data/Game.dcb", "Data/Game2.dcb"):
        try:
            raw = sc.p4k.getinfo(member).open("rb").read()
            return sorted({match.group(0).decode("ascii") for match in POOL_RE.finditer(raw)})
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


def minimal_pool_definition(pool_definition: dict[str, object]) -> dict[str, object]:
    if isinstance(pool_definition.get("variants"), list):
        return {"variants": pool_definition["variants"]}
    if isinstance(pool_definition.get("lines"), list):
        return {"lines": pool_definition["lines"]}
    item_refs = pool_definition.get("item_refs")
    if isinstance(item_refs, list):
        return {"item_refs": item_refs}
    raise ValueError("Definicion de pool invalida: falta `item_refs`, `lines` o `variants`")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap inicial de source/blueprints/pools.json a partir del overlay actual."
    )
    parser.add_argument("--overlay", default=str(DEFAULT_OVERLAY))
    parser.add_argument("--global-en", default=str(DEFAULT_GLOBAL_EN))
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--discovery-output", default=str(DEFAULT_DISCOVERY_OUTPUT))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    overlay_path = Path(args.overlay).expanduser().resolve()
    global_en_path = Path(args.global_en).expanduser().resolve()
    sc_root = Path(args.sc_root).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    discovery_output_path = Path(args.discovery_output).expanduser().resolve()
    template_path, pool_source_path = default_blueprint_source_paths(REPO_ROOT)

    if pool_source_path.exists() and not args.force:
        raise FileExistsError(
            f"Ya existe {pool_source_path}. Usa --force si quieres regenerarlo desde el overlay actual."
        )

    overlay = read_global_ini(overlay_path)
    english_map = read_global_ini(global_en_path).mapping
    pools = extract_pools(sc_root, cache_dir)

    lower_to_real = {key.lower(): key for key in overlay.mapping}
    grouped_descs: dict[str, list[dict[str, object]]] = defaultdict(list)

    for key in overlay.mapping:
        if not has_token(key, "title"):
            continue

        desc_guess = replace_token(key, "title", "desc")
        desc_key = lower_to_real.get(desc_guess.lower())
        if desc_key is None:
            continue

        desc_value = overlay.mapping[desc_key]
        candidate_pool, candidate_score = choose_candidate_pool(key, pools)
        grouped_descs[desc_value].append(
            {
                "title_key": key,
                "desc_key": desc_key,
                "english_title": english_map.get(key, key),
                "candidate_pool": candidate_pool,
                "candidate_score": candidate_score,
            }
        )

    used_pool_ids: set[str] = set()
    pool_definitions: dict[str, dict[str, object]] = {}
    mission_pool_map: dict[str, str] = {}

    sorted_groups = sorted(
        grouped_descs.items(),
        key=lambda item: (-len(item[1]), str(item[1][0]["desc_key"]).lower()),
    )

    for _index, (desc_value, missions) in enumerate(sorted_groups, start=1):
        candidate_counts = Counter(
            mission["candidate_pool"]
            for mission in missions
            if mission["candidate_pool"] is not None and int(mission["candidate_score"]) > 0
        )
        representative_desc_key = str(missions[0]["desc_key"])
        dominant_candidate = candidate_counts.most_common(1)[0][0] if candidate_counts else None

        if dominant_candidate is not None:
            pool_id_base = dominant_candidate
        else:
            pool_id_base = f"OVERLAY_{representative_desc_key}"

        pool_id = pool_id_base
        suffix = 2
        while pool_id in used_pool_ids:
            pool_id = f"{pool_id_base}__{suffix:02d}"
            suffix += 1
        used_pool_ids.add(pool_id)

        item_refs = list(dict.fromkeys(ITEM_REF_RE.findall(desc_value)))
        pool_definitions[pool_id] = {
            "representative_desc_key": representative_desc_key,
            "dominant_candidate_pool": dominant_candidate,
            "mission_count": len(missions),
            "overlay_value": desc_value,
            "item_refs": item_refs,
            "missions": [
                {
                    "title_key": str(mission["title_key"]),
                    "desc_key": str(mission["desc_key"]),
                    "english_title": str(mission["english_title"]),
                }
                for mission in sorted(missions, key=lambda item: str(item["title_key"]).lower())
            ],
        }

        for mission in missions:
            mission_pool_map[str(mission["desc_key"])] = pool_id

    template_entries = []
    for entry in overlay.entries:
        pool_id = mission_pool_map.get(entry.key)
        if pool_id is None:
            template_entries.append(entry)
            continue

        item_refs = pool_definitions[pool_id]["item_refs"]
        if not isinstance(item_refs, list) or not item_refs:
            template_entries.append(entry)
            continue

        parts = entry.value.split("\\n")
        item_line_indexes: list[int] = []

        for index, part in enumerate(parts):
            match = ITEM_LINE_RE.match(part)
            if match:
                item_line_indexes.append(index)

        if item_line_indexes:
            contiguous_start = item_line_indexes[0]
            contiguous_end = item_line_indexes[-1]
            rendered_item_lines = [f"- @{item_ref}@" for item_ref in item_refs]
            contiguous_lines = parts[contiguous_start : contiguous_end + 1]
            if (
                len(item_line_indexes) == len(rendered_item_lines)
                and item_line_indexes == list(range(contiguous_start, contiguous_end + 1))
                and contiguous_lines == rendered_item_lines
            ):
                parts = parts[:contiguous_start] + [f"@{pool_id}@"] + parts[contiguous_end + 1 :]

        template_entries.append(type(entry)(key=entry.key, value="\\n".join(parts)))

    template_path.parent.mkdir(parents=True, exist_ok=True)
    with template_path.open("w", encoding="utf-8", newline="\n") as handle:
        for entry in template_entries:
            handle.write(f"{entry.key}={entry.value}\n")

    minimal_payload = {
        "version": 1,
        "generated_from": {
            "overlay": str(overlay_path.relative_to(REPO_ROOT).as_posix()),
            "global_en": str(global_en_path.relative_to(REPO_ROOT).as_posix()),
        },
        "notes": [
            "Fuente minima para generar recompensas visibles de blueprints.",
            "Cada entrada de `mission_pool_map` enlaza una clave `desc` del overlay con una pool reutilizable.",
        ],
        "pools": {
            pool_id: minimal_pool_definition(pool_definition)
            for pool_id, pool_definition in sorted(pool_definitions.items(), key=lambda item: item[0].lower())
        },
        "mission_pool_map": dict(sorted(mission_pool_map.items(), key=lambda item: item[0].lower())),
    }

    with pool_source_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(minimal_payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    discovery_output_path.parent.mkdir(parents=True, exist_ok=True)
    discovery_payload = {
        "version": 1,
        "generated_from": minimal_payload["generated_from"],
        "notes": [
            "Artefacto auxiliar con contexto de discovery para revisar y refactorizar pools.",
            "No lo usa la build; la fuente efectiva es source/blueprints/pools.json.",
            "Los nombres `BP_MISSIONREWARD_*` son heurísticos cuando ha sido posible deducir una candidata desde Game2.dcb.",
        ],
        "pools": {
            pool_id: pool_definition
            for pool_id, pool_definition in sorted(pool_definitions.items(), key=lambda item: item[0].lower())
        },
        "mission_pool_map": dict(sorted(mission_pool_map.items(), key=lambda item: item[0].lower())),
    }

    with discovery_output_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(discovery_payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"Template generado: {template_path}")
    print(f"Fuente de pools generada: {pool_source_path}")
    print(f"Discovery de pools generado: {discovery_output_path}")
    print(f"Pools estructuradas: {len(pool_definitions)}")
    print(f"Mapeos de mision->pool: {len(mission_pool_map)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
