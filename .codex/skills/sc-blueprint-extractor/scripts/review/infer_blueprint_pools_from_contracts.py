from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from dcb_text_support import build_title_index, load_raw_dcb, split_strings_with_offsets
from runtime_support import REPO_ROOT


DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"
DEFAULT_GLOBAL = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_TEMPLATE = REPO_ROOT / "source" / "blueprints" / "blueprints_template.ini"
DEFAULT_POOLS = REPO_ROOT / "source" / "blueprints" / "pools.json"
DEFAULT_SHORTLIST = REPO_ROOT / "informes" / "BLUEPRINTS_NEW_MISSION_CANDIDATES_SHORTLIST.md"
DEFAULT_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_CONTRACT_TO_POOL_INFERENCE.md"
DEFAULT_EXPORTED_ROOT = REPO_ROOT / "data" / "starcitizen" / "extracts" / "current" / "game2" / "exported"

POOL_TOKEN_RE = re.compile(r"@(?P<pool>(?:BP_MISSIONREWARD|BP_REWARDS)_[A-Za-z0-9_]+)@")
TITLE_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
BLUEPRINT_POOL_PATH_RE = re.compile(
    r"libs/foundry/records/crafting/blueprintrewards/(?P<subdir>.+?)/(?P<name>[^/]+)\.json$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MissionInfo:
    title_key: str
    desc_key: str | None
    english_title: str


@dataclass(frozen=True)
class MissionSignals:
    contract_paths: tuple[str, ...]
    missiondata_paths: tuple[str, ...]


@dataclass(frozen=True)
class HardenedInference:
    kind: str
    values: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ExportedContractLink:
    title_keys: tuple[str, ...]
    desc_keys: tuple[str, ...]
    pool_ids: tuple[str, ...]
    template_path: str | None
    source_path: str


def read_ini_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw_line or raw_line.startswith((";", "#")) or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        mapping[key] = value
    return mapping


def _strip_loc_token(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if not value.startswith("@"):
        return None
    token = value.strip().strip("@")
    if not token or token.startswith("LOC_"):
        return None
    return token


def _walk_objects(payload: object) -> list[dict]:
    found: list[dict] = []
    stack: list[object] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            found.append(current)
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return found


def _resolve_exported_path(record_path: str, exported_root: Path) -> Path | None:
    match = BLUEPRINT_POOL_PATH_RE.search(record_path.replace("\\", "/"))
    if not match:
        return None
    return exported_root / "libs" / "foundry" / "records" / "crafting" / "blueprintrewards" / match.group("subdir") / f"{match.group('name')}.json"


def _resolve_pool_id(record_path: str, exported_root: Path, cache: dict[str, str | None]) -> str | None:
    cached = cache.get(record_path)
    if record_path in cache:
        return cached
    exported_path = _resolve_exported_path(record_path, exported_root)
    if exported_path is None or not exported_path.exists():
        cache[record_path] = None
        return None
    try:
        payload = json.loads(exported_path.read_text(encoding="utf-8"))
    except Exception:
        cache[record_path] = None
        return None
    record_name = payload.get("_RecordName_")
    if not isinstance(record_name, str) or "." not in record_name:
        cache[record_path] = None
        return None
    pool_id = record_name.split(".", 1)[1]
    cache[record_path] = pool_id
    return pool_id


def _extract_template_display_strings(template_path: str | None, exported_root: Path, cache: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    if not template_path:
        return ()
    cached = cache.get(template_path)
    if cached is not None:
        return cached
    normalized = template_path.replace("\\", "/")
    prefix = "file://./../../../../../"
    if normalized.startswith(prefix):
        relative = normalized[len(prefix):]
        local_path = exported_root / relative.replace("/", "\\")
    else:
        local_path = exported_root / normalized
    if not local_path.exists():
        cache[template_path] = ()
        return ()
    try:
        payload = json.loads(local_path.read_text(encoding="utf-8"))
    except Exception:
        cache[template_path] = ()
        return ()
    display = (
        payload.get("_RecordValue_", {})
        .get("contractDisplayInfo", {})
        .get("displayString", [])
    )
    tokens = tuple(
        token
        for token in (_strip_loc_token(value) for value in display)
        if token is not None
    )
    cache[template_path] = tokens
    return tokens


def collect_exported_contract_links(exported_root: Path) -> list[ExportedContractLink]:
    contract_root = exported_root / "libs" / "foundry" / "records" / "contracts" / "contractgenerator"
    if not contract_root.exists():
        return []

    template_cache: dict[str, tuple[str, ...]] = {}
    pool_cache: dict[str, str | None] = {}
    links: list[ExportedContractLink] = []

    for path in sorted(contract_root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        for node in _walk_objects(payload):
            if "contractResults" not in node and "paramOverrides" not in node and "template" not in node:
                continue

            template_path = node.get("template") if isinstance(node.get("template"), str) else None
            title_keys: list[str] = []
            desc_keys: list[str] = []

            param_overrides = node.get("paramOverrides")
            if isinstance(param_overrides, dict):
                for override in param_overrides.get("stringParamOverrides", []):
                    if not isinstance(override, dict):
                        continue
                    token = _strip_loc_token(override.get("value"))
                    if token is None:
                        continue
                    param = override.get("param")
                    if param == "Title":
                        title_keys.append(token)
                    elif param == "Description":
                        desc_keys.append(token)

            if not title_keys and not desc_keys:
                template_tokens = _extract_template_display_strings(template_path, exported_root, template_cache)
                if template_tokens:
                    title_keys.extend(template_tokens[:2])
                    if len(template_tokens) >= 3:
                        desc_keys.append(template_tokens[2])

            pool_ids: list[str] = []
            contract_results = node.get("contractResults")
            if isinstance(contract_results, dict):
                for result in _walk_objects(contract_results):
                    blueprint_pool_path = result.get("blueprintPool")
                    if not isinstance(blueprint_pool_path, str):
                        continue
                    pool_id = _resolve_pool_id(blueprint_pool_path, exported_root, pool_cache)
                    if pool_id:
                        pool_ids.append(pool_id)

            title_keys = list(dict.fromkeys(title_keys))
            desc_keys = list(dict.fromkeys(desc_keys))
            pool_ids = list(dict.fromkeys(pool_ids))
            if not pool_ids or (not title_keys and not desc_keys):
                continue

            links.append(
                ExportedContractLink(
                    title_keys=tuple(title_keys),
                    desc_keys=tuple(desc_keys),
                    pool_ids=tuple(pool_ids),
                    template_path=template_path,
                    source_path=str(path.relative_to(exported_root)).replace("\\", "/"),
                )
            )

    return links


def build_direct_exported_pool_map(links: list[ExportedContractLink]) -> tuple[dict[str, Counter[str]], dict[str, list[ExportedContractLink]]]:
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    sources: dict[str, list[ExportedContractLink]] = defaultdict(list)
    for link in links:
        for key in (*link.title_keys, *link.desc_keys):
            counters[key].update(link.pool_ids)
            sources[key].append(link)
    return counters, sources


def parse_shortlist(path: Path, global_map: dict[str, str]) -> list[MissionInfo]:
    entries: list[MissionInfo] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.startswith("| `"):
            continue
        parts = [part.strip() for part in raw_line.strip("|").split("|")]
        if len(parts) != 5:
            continue
        title_key = parts[1].strip("`")
        desc_key = parts[2].strip("`")
        if title_key in seen:
            continue
        seen.add(title_key)
        entries.append(
            MissionInfo(
                title_key=title_key,
                desc_key=desc_key,
                english_title=global_map.get(title_key, parts[3].strip("`")),
            )
        )
    return entries


def collect_template_missions(template_map: dict[str, str], global_map: dict[str, str]) -> list[MissionInfo]:
    missions: list[MissionInfo] = []
    for key in template_map:
        lower = key.lower()
        if "title" not in lower:
            continue
        desc_key = key.replace("Title", "Desc").replace("title", "desc")
        missions.append(
            MissionInfo(
                title_key=key,
                desc_key=desc_key if desc_key in template_map else None,
                english_title=global_map.get(key, key),
            )
        )
    return missions


def extract_nearby_paths(
    strings: list[tuple[int, str]],
    title_index: dict[str, int],
    title_key: str,
    *,
    needle: str,
    window: int = 12000,
    distance_slop: int = 1024,
) -> list[str]:
    offset = title_index.get(title_key)
    if offset is None:
        return []
    start = offset - window
    end = offset + window
    distances: dict[str, int] = {}
    for pos, value in strings:
        if pos < start:
            continue
        if pos > end:
            break
        if needle not in value.lower():
            continue
        distance = abs(pos - offset)
        previous = distances.get(value)
        if previous is None or distance < previous:
            distances[value] = distance
    if not distances:
        return []
    best_distance = min(distances.values())
    selected = [
        path
        for path, distance in sorted(distances.items(), key=lambda item: (item[1], item[0]))
        if distance <= best_distance + distance_slop
    ]
    return selected


def extract_missiondata_paths(strings: list[tuple[int, str]], title_index: dict[str, int], title_key: str) -> list[str]:
    return extract_nearby_paths(
        strings,
        title_index,
        title_key,
        needle="missiondata/",
        window=12000,
        distance_slop=1536,
    )


def resolve_known_pools(template_map: dict[str, str], pools_data: dict) -> dict[str, str]:
    known: dict[str, str] = {}
    mission_pool_map = pools_data.get("mission_pool_map", {})
    for desc_key, pool_name in mission_pool_map.items():
        if isinstance(pool_name, str):
            known[desc_key] = pool_name
        elif isinstance(pool_name, list):
            string_values = [value for value in pool_name if isinstance(value, str)]
            if len(string_values) == 1:
                known[desc_key] = string_values[0]
    for key, value in template_map.items():
        pools = list(dict.fromkeys(match.group("pool") for match in POOL_TOKEN_RE.finditer(value)))
        if len(pools) == 1:
            known.setdefault(key, pools[0])
    return known


def normalize_title_tokens(title_key: str) -> set[str]:
    ignored = {"title", "desc", "name", "001", "002", "003", "004", "01", "02", "03", "04"}
    return {
        token.lower()
        for token in TITLE_TOKEN_RE.findall(title_key)
        if token.lower() not in ignored and not token.isdigit()
    }


def token_affinity_score(left: str, right: str) -> int:
    return len(normalize_title_tokens(left) & normalize_title_tokens(right))


def infer_family_specific(
    mission: MissionInfo,
    signals: MissionSignals,
    matched_strict: dict[tuple[str, tuple[str, ...]], Counter[str]],
) -> HardenedInference | None:
    title_lower = mission.title_key.lower()
    contract_paths = {path.lower() for path in signals.contract_paths}

    if "shubin_resourcegathering_fpsmining.xml" in "".join(contract_paths):
        if "stanton" in title_lower:
            return HardenedInference(
                kind="single_pool",
                values=("BP_MISSIONREWARD_Shubin_ResourceGathering_FPSMining_Stanton",),
                reason="La familia Shubin FPS mining ya resuelta en el template separa Stanton frente a Pyro/Nyx por localidad en la propia key.",
            )
        if "pyro" in title_lower or "nyx" in title_lower:
            return HardenedInference(
                kind="single_pool",
                values=("BP_MISSIONREWARD_Shubin_ResourceGathering_FPSMining_Pyro",),
                reason="La familia Shubin FPS mining ya resuelta en el template agrupa Nyx con Pyro en la misma pool visible.",
            )

    if "shubin_resourcegathering_shipmining.xml" in "".join(contract_paths):
        if "_org_" in title_lower:
            return HardenedInference(
                kind="composite_pool",
                values=(
                    "BP_MISSIONREWARD_Shubin_ResourceGathering_ShipMining_PyroNyx",
                    "BP_MISSIONREWARD_Shubin_ResourceGathering_ShipMining_Stanton",
                ),
                reason="La variante Org ya existente en el template renderiza ambas pools por region (`pyronyx` y `stanton`), no una sola pool.",
            )
        if "stanton" in title_lower:
            return HardenedInference(
                kind="single_pool",
                values=("BP_MISSIONREWARD_Shubin_ResourceGathering_ShipMining_Stanton",),
                reason="La familia Shubin ship mining ya resuelta en el template separa Stanton frente a Pyro/Nyx por localidad en la propia key.",
            )
        if "pyro" in title_lower or "nyx" in title_lower:
            return HardenedInference(
                kind="single_pool",
                values=("BP_MISSIONREWARD_Shubin_ResourceGathering_ShipMining_PyroNyx",),
                reason="La familia Shubin ship mining ya resuelta en el template agrupa Nyx con Pyro en la misma pool visible.",
            )

    return None


def build_signals(strings: list[tuple[int, str]], title_index: dict[str, int], title_key: str) -> MissionSignals:
    return MissionSignals(
        contract_paths=tuple(
            extract_nearby_paths(
                strings,
                title_index,
                title_key,
                needle="contracts/contractgenerator/",
                window=12000,
                distance_slop=768,
            )
        ),
        missiondata_paths=tuple(extract_missiondata_paths(strings, title_index, title_key)),
    )


def build_report(
    *,
    template_missions: list[MissionInfo],
    shortlist_missions: list[MissionInfo],
    template_map: dict[str, str],
    known_desc_pools: dict[str, str],
    strings: list[tuple[int, str]],
    exported_root: Path,
    output_path: Path,
) -> str:
    title_index = build_title_index(strings)
    exported_links = collect_exported_contract_links(exported_root)
    direct_pool_map, direct_pool_sources = build_direct_exported_pool_map(exported_links)

    contract_to_pools: dict[str, Counter[str]] = defaultdict(Counter)
    contract_missiondata_to_pools: dict[tuple[str, tuple[str, ...]], Counter[str]] = defaultdict(Counter)
    contract_missiondata_pool_titles: dict[tuple[str, tuple[str, ...], str], list[str]] = defaultdict(list)
    for mission in template_missions:
        if not mission.desc_key:
            continue
        pool = known_desc_pools.get(mission.desc_key)
        if not pool:
            continue
        signals = build_signals(strings, title_index, mission.title_key)
        for contract_path in signals.contract_paths:
            contract_to_pools[contract_path][pool] += 1
            contract_missiondata_to_pools[(contract_path, signals.missiondata_paths)][pool] += 1
            contract_missiondata_pool_titles[(contract_path, signals.missiondata_paths, pool)].append(mission.title_key)

    inferred_direct: list[tuple[MissionInfo, tuple[str, ...], list[ExportedContractLink]]] = []
    inferred_strict: list[tuple[MissionInfo, str, str, tuple[str, ...], Counter[str]]] = []
    inferred_contract_only: list[tuple[MissionInfo, str, str, Counter[str]]] = []
    inferred_hardened: list[tuple[MissionInfo, HardenedInference, MissionSignals]] = []
    ambiguous: list[tuple[MissionInfo, MissionSignals, dict[str, Counter[str]], dict[tuple[str, tuple[str, ...]], Counter[str]]]] = []
    missing_contract: list[MissionInfo] = []

    for mission in shortlist_missions:
        direct_counter = Counter()
        direct_sources: list[ExportedContractLink] = []
        for key in (mission.title_key, mission.desc_key):
            if not key:
                continue
            direct_counter.update(direct_pool_map.get(key, Counter()))
            direct_sources.extend(direct_pool_sources.get(key, []))
        direct_unique = sorted(direct_counter)
        if direct_unique:
            direct_sources = list(dict.fromkeys(direct_sources))
            if len(direct_unique) == 1:
                inferred_direct.append((mission, tuple(direct_unique), direct_sources))
                continue

        signals = build_signals(strings, title_index, mission.title_key)
        if not signals.contract_paths:
            missing_contract.append(mission)
            continue
        matched_contracts = {path: contract_to_pools[path] for path in signals.contract_paths if contract_to_pools.get(path)}
        matched_strict = {
            (path, signals.missiondata_paths): contract_missiondata_to_pools[(path, signals.missiondata_paths)]
            for path in signals.contract_paths
            if contract_missiondata_to_pools.get((path, signals.missiondata_paths))
        }
        if matched_strict:
            unique_pools = sorted({pool for counter in matched_strict.values() for pool in counter})
            if len(unique_pools) == 1:
                contract_path, missiondata_paths = next(iter(matched_strict))
                inferred_strict.append(
                    (mission, unique_pools[0], contract_path, missiondata_paths, matched_strict[(contract_path, missiondata_paths)])
                )
                continue
        if not matched_contracts:
            missing_contract.append(mission)
            continue
        unique_pools = sorted({pool for counter in matched_contracts.values() for pool in counter})
        if len(unique_pools) == 1:
            inferred_contract_only.append((mission, unique_pools[0], signals.contract_paths[0], matched_contracts[next(iter(matched_contracts))]))
        else:
            hardened = infer_family_specific(mission, signals, matched_strict)
            if hardened:
                inferred_hardened.append((mission, hardened, signals))
            else:
                ambiguous.append((mission, signals, matched_contracts, matched_strict))

    lines: list[str] = []
    lines.append("# Inferencia pool real desde contratos del juego")
    lines.append("")
    lines.append("Metodo:")
    lines.append("- Aprender `contractgenerator/*.xml -> pool` usando solo misiones ya presentes en el template.")
    lines.append("- Aplicar ese mapa a misiones nuevas que compartan exactamente la misma ruta de contrato detectada en `Game2.dcb`.")
    lines.append("- No usa heuristica de nombres de mision; solo reutiliza contratos detectados en el binario.")
    lines.append("")
    lines.append("Resumen:")
    lines.append(f"- Misiones template evaluadas: {len(template_missions)}")
    lines.append(f"- Enlaces directos exportados (`title/desc -> blueprintPool`): {len(exported_links)}")
    lines.append(f"- Contratos con al menos una pool observada: {len(contract_to_pools)}")
    lines.append(f"- Misiones nuevas con inferencia directa desde export JSON: {len(inferred_direct)}")
    lines.append(f"- Misiones nuevas con inferencia unica estricta (contrato + missiondata): {len(inferred_strict)}")
    lines.append(f"- Misiones nuevas con inferencia unica solo por contrato: {len(inferred_contract_only)}")
    lines.append(f"- Misiones nuevas resueltas por endurecimiento especifico de familia: {len(inferred_hardened)}")
    lines.append(f"- Misiones nuevas con contrato pero varias pools posibles: {len(ambiguous)}")
    lines.append(f"- Misiones nuevas sin contrato util o sin aprendizaje previo: {len(missing_contract)}")
    lines.append("")

    lines.append("## Inferencias Directas Desde Export JSON")
    lines.append("")
    if inferred_direct:
        lines.append("| Titulo ingles | `title` | `desc` | Pool inferida | Fuentes |")
        lines.append("|---|---|---|---|---|")
        for mission, pools, sources in inferred_direct:
            rendered_pools = "<br>".join(f"`{pool}`" for pool in pools)
            rendered_sources = "<br>".join(f"`{source.source_path}`" for source in sources[:4])
            lines.append(
                f"| `{mission.english_title}` | `{mission.title_key}` | `{mission.desc_key or 'n/d'}` | {rendered_pools} | {rendered_sources} |"
            )
    else:
        lines.append("Sin inferencias directas.")
    lines.append("")

    lines.append("## Contrato + Missiondata A Pool")
    lines.append("")
    lines.append("| Contrato | Missiondata | Pools observadas |")
    lines.append("|---|---|---|")
    for contract_path, missiondata_paths in sorted(contract_missiondata_to_pools):
        observed = "<br>".join(
            f"`{pool}` x{count}" for pool, count in contract_missiondata_to_pools[(contract_path, missiondata_paths)].most_common()
        )
        missiondata = "<br>".join(f"`{path}`" for path in missiondata_paths) if missiondata_paths else "`(sin missiondata)`"
        lines.append(f"| `{contract_path}` | {missiondata} | {observed} |")
    lines.append("")

    lines.append("## Contrato A Pool")
    lines.append("")
    lines.append("| Contrato | Pools observadas |")
    lines.append("|---|---|")
    for contract_path in sorted(contract_to_pools):
        observed = "<br>".join(f"`{pool}` x{count}" for pool, count in contract_to_pools[contract_path].most_common())
        lines.append(f"| `{contract_path}` | {observed} |")
    lines.append("")

    lines.append("## Inferencias Unicas Estrictas")
    lines.append("")
    if inferred_strict:
        lines.append("| Titulo ingles | `title` | `desc` | Contrato | Missiondata | Pool inferida |")
        lines.append("|---|---|---|---|---|---|")
        for mission, pool, contract_path, missiondata_paths, _counter in inferred_strict:
            missiondata = "<br>".join(f"`{path}`" for path in missiondata_paths) if missiondata_paths else "`(sin missiondata)`"
            lines.append(
                f"| `{mission.english_title}` | `{mission.title_key}` | `{mission.desc_key or 'n/d'}` | `{contract_path}` | {missiondata} | `{pool}` |"
            )
    else:
        lines.append("Sin inferencias estrictas.")
    lines.append("")

    lines.append("## Inferencias Unicas Solo Por Contrato")
    lines.append("")
    if inferred_contract_only:
        lines.append("| Titulo ingles | `title` | `desc` | Contrato | Pool inferida |")
        lines.append("|---|---|---|---|---|")
        for mission, pool, contract_path, _counter in inferred_contract_only:
            lines.append(
                f"| `{mission.english_title}` | `{mission.title_key}` | `{mission.desc_key or 'n/d'}` | `{contract_path}` | `{pool}` |"
            )
    else:
        lines.append("Sin inferencias solo por contrato.")
    lines.append("")

    lines.append("## Inferencias Endurecidas Por Familia")
    lines.append("")
    if inferred_hardened:
        lines.append("| Titulo ingles | `title` | `desc` | Resultado | Motivo |")
        lines.append("|---|---|---|---|---|")
        for mission, hardened, _signals in inferred_hardened:
            if hardened.kind == "single_pool":
                rendered = f"`{hardened.values[0]}`"
            else:
                rendered = "<br>".join(f"`{value}`" for value in hardened.values)
            lines.append(
                f"| `{mission.english_title}` | `{mission.title_key}` | `{mission.desc_key or 'n/d'}` | {rendered} | {hardened.reason} |"
            )
    else:
        lines.append("Sin inferencias endurecidas por familia.")
    lines.append("")

    lines.append("## Ambiguas")
    lines.append("")
    if ambiguous:
        for mission, signals, matched_contracts, matched_strict in ambiguous[:80]:
            lines.append(f"### {mission.english_title}")
            lines.append("")
            lines.append(f"- `title`: `{mission.title_key}`")
            lines.append(f"- `desc`: `{mission.desc_key or 'n/d'}`")
            if signals.missiondata_paths:
                lines.append(
                    f"- Missiondata detectado: {', '.join(f'`{path}`' for path in signals.missiondata_paths)}"
                )
            for contract_path in signals.contract_paths:
                counter = matched_contracts.get(contract_path)
                if not counter:
                    continue
                lines.append(f"- Contrato: `{contract_path}`")
                lines.append(
                    f"- Pools observadas: {', '.join(f'`{pool}` x{count}' for pool, count in counter.most_common())}"
                )
                strict_counter = matched_strict.get((contract_path, signals.missiondata_paths))
                if strict_counter:
                    lines.append(
                        f"- Pools con mismo missiondata: {', '.join(f'`{pool}` x{count}' for pool, count in strict_counter.most_common())}"
                    )
                    affinity_rows: list[tuple[int, str, str]] = []
                    for pool in strict_counter:
                        examples = contract_missiondata_pool_titles.get((contract_path, signals.missiondata_paths, pool), [])
                        if not examples:
                            continue
                        best_example = max(examples, key=lambda example: token_affinity_score(mission.title_key, example))
                        affinity_rows.append((token_affinity_score(mission.title_key, best_example), pool, best_example))
                    if affinity_rows:
                        affinity_rows.sort(key=lambda row: (-row[0], row[1], row[2]))
                        lines.append(
                            "- Afinidad por `title_key`: "
                            + ", ".join(
                                f"`{pool}` score={score} via `{example}`"
                                for score, pool, example in affinity_rows
                            )
                        )
            lines.append("")
    else:
        lines.append("Sin casos ambiguos.")
        lines.append("")

    report = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Infiere pools desde contratos detectados en Game2.dcb.")
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--global-ini", default=str(DEFAULT_GLOBAL))
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--pools", default=str(DEFAULT_POOLS))
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST))
    parser.add_argument("--exported-root", default=str(DEFAULT_EXPORTED_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    global_map = read_ini_map(Path(args.global_ini).expanduser().resolve())
    template_map = read_ini_map(Path(args.template).expanduser().resolve())
    pools_data = json.loads(Path(args.pools).expanduser().resolve().read_text(encoding="utf-8"))
    shortlist_missions = parse_shortlist(Path(args.shortlist).expanduser().resolve(), global_map)
    template_missions = collect_template_missions(template_map, global_map)
    known_desc_pools = resolve_known_pools(template_map, pools_data)
    _dcb_member, raw = load_raw_dcb(
        Path(args.sc_root).expanduser().resolve(),
        Path(args.cache_dir).expanduser().resolve(),
    )
    strings = split_strings_with_offsets(raw)
    build_report(
        template_missions=template_missions,
        shortlist_missions=shortlist_missions,
        template_map=template_map,
        known_desc_pools=known_desc_pools,
        strings=strings,
        exported_root=Path(args.exported_root).expanduser().resolve(),
        output_path=Path(args.output).expanduser().resolve(),
    )
    print(Path(args.output).expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
