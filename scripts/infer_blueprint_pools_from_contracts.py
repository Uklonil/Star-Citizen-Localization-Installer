from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from scdatatools.sc import StarCitizen

from extract_blueprint_mission_rewards import find_datacore_member


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"
DEFAULT_GLOBAL = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_TEMPLATE = REPO_ROOT / "source" / "blueprints" / "blueprints_template.ini"
DEFAULT_POOLS = REPO_ROOT / "source" / "blueprints" / "pools.json"
DEFAULT_SHORTLIST = REPO_ROOT / "informes" / "BLUEPRINTS_NEW_MISSION_CANDIDATES_SHORTLIST.md"
DEFAULT_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_CONTRACT_TO_POOL_INFERENCE.md"

POOL_TOKEN_RE = re.compile(r"@(?P<pool>BP_MISSIONREWARD_[A-Za-z0-9_]+)@")
TITLE_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


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


def read_ini_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw_line or raw_line.startswith((";", "#")) or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        mapping[key] = value
    return mapping


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


def load_raw_dcb(sc_root: Path, cache_dir: Path) -> bytes:
    sc = StarCitizen(sc_root, cache_dir=cache_dir)
    dcb_member = find_datacore_member(sc)
    if dcb_member is None:
        raise FileNotFoundError("No se encontro Data/Game.dcb ni Data/Game2.dcb en la instalacion.")
    return sc.p4k.getinfo(dcb_member).open("rb").read()


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
        known[desc_key] = pool_name
    for key, value in template_map.items():
        pools = list(dict.fromkeys(match.group("pool") for match in POOL_TOKEN_RE.finditer(value)))
        if len(pools) == 1:
            known.setdefault(key, pools[0])
    return known


def normalize_title_tokens(title_key: str) -> set[str]:
    ignored = {
        "title",
        "desc",
        "name",
        "001",
        "002",
        "003",
        "004",
        "01",
        "02",
        "03",
        "04",
    }
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
    output_path: Path,
) -> str:
    title_index = build_title_index(strings)

    contract_to_pools: dict[str, Counter[str]] = defaultdict(Counter)
    contract_missiondata_to_pools: dict[tuple[str, tuple[str, ...]], Counter[str]] = defaultdict(Counter)
    contract_missiondata_pool_titles: dict[tuple[str, tuple[str, ...], str], list[str]] = defaultdict(list)
    title_signals: dict[str, MissionSignals] = {}
    for mission in template_missions:
        if not mission.desc_key:
            continue
        pool = known_desc_pools.get(mission.desc_key)
        if not pool:
            continue
        signals = build_signals(strings, title_index, mission.title_key)
        title_signals[mission.title_key] = signals
        for contract_path in signals.contract_paths:
            contract_to_pools[contract_path][pool] += 1
            contract_missiondata_to_pools[(contract_path, signals.missiondata_paths)][pool] += 1
            contract_missiondata_pool_titles[(contract_path, signals.missiondata_paths, pool)].append(mission.title_key)

    inferred_strict: list[tuple[MissionInfo, str, str, tuple[str, ...], Counter[str]]] = []
    inferred_contract_only: list[tuple[MissionInfo, str, str, Counter[str]]] = []
    inferred_hardened: list[tuple[MissionInfo, HardenedInference, MissionSignals]] = []
    ambiguous: list[tuple[MissionInfo, MissionSignals, dict[str, Counter[str]], dict[tuple[str, tuple[str, ...]], Counter[str]]]] = []
    missing_contract: list[MissionInfo] = []

    for mission in shortlist_missions:
        signals = build_signals(strings, title_index, mission.title_key)
        title_signals[mission.title_key] = signals
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
    lines.append(f"- Contratos con al menos una pool observada: {len(contract_to_pools)}")
    lines.append(f"- Misiones nuevas con inferencia unica estricta (contrato + missiondata): {len(inferred_strict)}")
    lines.append(f"- Misiones nuevas con inferencia unica solo por contrato: {len(inferred_contract_only)}")
    lines.append(f"- Misiones nuevas resueltas por endurecimiento especifico de familia: {len(inferred_hardened)}")
    lines.append(f"- Misiones nuevas con contrato pero varias pools posibles: {len(ambiguous)}")
    lines.append(f"- Misiones nuevas sin contrato util o sin aprendizaje previo: {len(missing_contract)}")
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
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    global_map = read_ini_map(Path(args.global_ini).expanduser().resolve())
    template_map = read_ini_map(Path(args.template).expanduser().resolve())
    pools_data = json.loads(Path(args.pools).expanduser().resolve().read_text(encoding="utf-8"))
    shortlist_missions = parse_shortlist(Path(args.shortlist).expanduser().resolve(), global_map)
    template_missions = collect_template_missions(template_map, global_map)
    known_desc_pools = resolve_known_pools(template_map, pools_data)
    raw = load_raw_dcb(Path(args.sc_root).expanduser().resolve(), Path(args.cache_dir).expanduser().resolve())
    strings = split_strings_with_offsets(raw)
    build_report(
        template_missions=template_missions,
        shortlist_missions=shortlist_missions,
        template_map=template_map,
        known_desc_pools=known_desc_pools,
        strings=strings,
        output_path=Path(args.output).expanduser().resolve(),
    )
    print(Path(args.output).expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
