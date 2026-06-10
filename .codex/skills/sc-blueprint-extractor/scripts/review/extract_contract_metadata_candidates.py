from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import REPO_ROOT
from review_support import read_ini_map


DEFAULT_CONTRACTS = "https://raw.githubusercontent.com/MrKraken/StarStrings/refs/heads/master/contracts.ini"
DEFAULT_POOLS = REPO_ROOT / "source" / "blueprints" / "pools.json"
DEFAULT_GLOBAL = REPO_ROOT / "distribucion" / "global.ini"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "starcitizen" / "reports" / "blueprints" / "contracts_metadata_candidates.json"
DEFAULT_REPORT_OUTPUT = REPO_ROOT / "informes" / "CONTRACTS_METADATA_EXTRACTION_REPORT.md"

EM4_BLOCK_RE = re.compile(r"<EM4>(.*?)</EM4>")
REP_TITLE_RE = re.compile(r"\[(?P<rep>[0-9/\- ]+)\s+Rep\]")
BLUEPRINT_TITLE_RE = re.compile(r"\[(?P<flag>BP)\](?P<uncertain>\*)?")
REPUTATION_AWARDED_RE = re.compile(r"Reputation Awarded(?: \(by difficulty\))?:</EM4>\s*([^<]+)")
SCENARIO_POINTS_RE = re.compile(r"Scenario Progress Points\s+([0-9/]+)")
VARIANT_TIER_RE = re.compile(r"Awarded from\s+(.+?)\s+level variants", re.IGNORECASE)
POOL_HEADER_RE = re.compile(r"Pool\s+\d+", re.IGNORECASE)
ITEM_LINE_RE = re.compile(r"^\s*-\s+(.+?)\s*$")


def normalize_key(key: str) -> str:
    return key.lstrip("\ufeff").split(",", 1)[0]


def load_contract_entries(source: str) -> dict[str, str]:
    if re.match(r"^https?://", source):
        with urllib.request.urlopen(source) as response:
            text = response.read().decode("utf-8-sig")
    else:
        text = Path(source).read_text(encoding="utf-8-sig")

    mapping: dict[str, str] = {}
    for raw_line in text.splitlines():
        if not raw_line or raw_line.startswith((";", "#")) or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        mapping[key.lstrip("\ufeff")] = value
    return mapping


def load_pool_source(path: Path) -> tuple[dict[str, dict], dict[str, object], dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    pools = payload.get("pools", {})
    mission_pool_map = payload.get("mission_pool_map", {})
    normalized_map = {normalize_key(key): value for key, value in mission_pool_map.items()}
    return pools, mission_pool_map, normalized_map


def normalize_pool_refs(raw_value: object) -> list[str]:
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value]
    return []


def parse_title_metadata(value: str) -> dict[str, object] | None:
    suffix_blocks = EM4_BLOCK_RE.findall(value)
    if not suffix_blocks:
        return None

    rep_ranges: list[str] = []
    blueprint_flag = False
    blueprint_flag_uncertain = False
    for block in suffix_blocks:
        rep_ranges.extend(match.group("rep").strip() for match in REP_TITLE_RE.finditer(block))
        for match in BLUEPRINT_TITLE_RE.finditer(block):
            blueprint_flag = True
            blueprint_flag_uncertain = blueprint_flag_uncertain or bool(match.group("uncertain"))

    if not rep_ranges and not blueprint_flag:
        return None

    raw_suffix = "".join(f"<EM4>{block}</EM4>" for block in suffix_blocks if REP_TITLE_RE.search(block) or BLUEPRINT_TITLE_RE.search(block))
    return {
        "blueprint_flag": blueprint_flag,
        "blueprint_flag_uncertain": blueprint_flag_uncertain,
        "rep_ranges": rep_ranges,
        "raw_suffix": raw_suffix,
    }


def extract_blueprint_block_lines(value: str) -> list[str]:
    lines = value.split("\\n")
    collecting = False
    collected: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if "Potential Blueprints" in line or "Multiple Blueprint Pools" in line:
            collecting = True
            continue
        if not collecting:
            continue
        if not line:
            continue
        if "Awarded from " in line or POOL_HEADER_RE.search(line):
            collected.append(line)
            continue
        if ITEM_LINE_RE.match(line):
            collected.append(line)
            continue
        if line.startswith("<EM4>") and "Blueprint" in line:
            collected.append(line)
            continue
    return collected


def parse_description_metadata(value: str) -> dict[str, object] | None:
    reputation_awarded = [
        match.group(1).replace("\\n", " ").strip()
        for match in REPUTATION_AWARDED_RE.finditer(value)
    ]
    scenario_progress_points = [match.group(1).strip() for match in SCENARIO_POINTS_RE.finditer(value)]
    blueprint_variant_tiers = [match.group(1).strip() for match in VARIANT_TIER_RE.finditer(value)]
    pool_headers = [match.group(0) for match in POOL_HEADER_RE.finditer(value)]
    has_potential_blueprints_block = "Potential Blueprints" in value
    has_multiple_blueprint_pools = "Multiple Blueprint Pools" in value
    raw_block_lines = extract_blueprint_block_lines(value)

    if not any(
        [
            reputation_awarded,
            scenario_progress_points,
            blueprint_variant_tiers,
            pool_headers,
            has_potential_blueprints_block,
            has_multiple_blueprint_pools,
            raw_block_lines,
        ]
    ):
        return None

    return {
        "reputation_awarded": reputation_awarded,
        "scenario_progress_points": scenario_progress_points,
        "blueprint_variant_tiers": blueprint_variant_tiers,
        "pool_headers": pool_headers,
        "has_potential_blueprints_block": has_potential_blueprints_block,
        "has_multiple_blueprint_pools": has_multiple_blueprint_pools,
        "raw_block_lines": raw_block_lines,
    }


def classify_blueprint_context(
    *,
    normalized_key: str,
    desc_meta: dict[str, object],
    normalized_pool_map: dict[str, object],
) -> dict[str, object]:
    raw_pool_refs = normalized_pool_map.get(normalized_key)
    local_pool_ids = normalize_pool_refs(raw_pool_refs)
    variant_tiers = desc_meta.get("blueprint_variant_tiers", [])
    pool_headers = desc_meta.get("pool_headers", [])
    has_bp_block = bool(desc_meta.get("has_potential_blueprints_block")) or bool(desc_meta.get("has_multiple_blueprint_pools"))

    if pool_headers or desc_meta.get("has_multiple_blueprint_pools"):
        classification = "candidate-new-pool-shape"
    elif has_bp_block and local_pool_ids and variant_tiers:
        classification = "new-tier-label-only"
    elif has_bp_block and local_pool_ids:
        classification = "already-covered"
    elif has_bp_block:
        classification = "candidate-new-pool-shape"
    else:
        classification = "new-metadata-only"

    return {
        "classification": classification,
        "local_pool_ids": local_pool_ids,
        "local_pool_count": len(local_pool_ids),
        "variant_label_tokens": list(variant_tiers),
        "pool_count": len(pool_headers) if pool_headers else (1 if has_bp_block else 0),
        "raw_block_lines": desc_meta.get("raw_block_lines", []),
    }


def build_payload(
    *,
    contracts_map: dict[str, str],
    global_map: dict[str, str],
    normalized_pool_map: dict[str, object],
) -> dict[str, object]:
    titles: dict[str, dict[str, object]] = {}
    descriptions: dict[str, dict[str, object]] = {}
    blueprint_context: dict[str, dict[str, object]] = {}
    normalized_global_keys = {normalize_key(local_key) for local_key in global_map}

    for key, value in contracts_map.items():
        title_meta = parse_title_metadata(value)
        if title_meta is not None:
            titles[key] = title_meta

        desc_meta = parse_description_metadata(value)
        if desc_meta is None:
            continue

        normalized_key = normalize_key(key)
        descriptions[key] = {
            "reputation_awarded": desc_meta["reputation_awarded"],
            "scenario_progress_points": desc_meta["scenario_progress_points"],
            "blueprint_variant_tiers": desc_meta["blueprint_variant_tiers"],
            "pool_headers": desc_meta["pool_headers"],
            "has_potential_blueprints_block": desc_meta["has_potential_blueprints_block"],
            "has_multiple_blueprint_pools": desc_meta["has_multiple_blueprint_pools"],
            "present_in_local_global": normalized_key in normalized_global_keys,
        }
        blueprint_context[key] = classify_blueprint_context(
            normalized_key=normalized_key,
            desc_meta=desc_meta,
            normalized_pool_map=normalized_pool_map,
        )

    return {
        "source": "contracts.ini",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "titles": titles,
        "descriptions": descriptions,
        "blueprint_context": blueprint_context,
    }


def build_markdown_report(*, payload: dict[str, object], source_value: str, report_output: Path) -> None:
    titles: dict[str, dict[str, object]] = payload["titles"]  # type: ignore[assignment]
    descriptions: dict[str, dict[str, object]] = payload["descriptions"]  # type: ignore[assignment]
    blueprint_context: dict[str, dict[str, object]] = payload["blueprint_context"]  # type: ignore[assignment]

    title_rows = sorted(
        (
            key,
            meta["blueprint_flag"],
            meta["blueprint_flag_uncertain"],
            ", ".join(meta["rep_ranges"]),
        )
        for key, meta in titles.items()
    )
    desc_with_rep = sorted((key, ", ".join(meta["reputation_awarded"])) for key, meta in descriptions.items() if meta["reputation_awarded"])
    desc_with_points = sorted((key, ", ".join(meta["scenario_progress_points"])) for key, meta in descriptions.items() if meta["scenario_progress_points"])
    desc_with_tiers = sorted((key, ", ".join(meta["blueprint_variant_tiers"])) for key, meta in descriptions.items() if meta["blueprint_variant_tiers"])
    multi_pool_rows = sorted(
        (
            key,
            context["classification"],
            ", ".join(context["local_pool_ids"]),
            ", ".join(descriptions[key]["pool_headers"]),
        )
        for key, context in blueprint_context.items()
        if descriptions[key]["has_multiple_blueprint_pools"] or descriptions[key]["pool_headers"]
    )

    class_counts: dict[str, int] = {}
    for context in blueprint_context.values():
        classification = str(context["classification"])
        class_counts[classification] = class_counts.get(classification, 0) + 1

    lines: list[str] = []
    lines.append("# Contracts Metadata Extraction Report")
    lines.append("")
    lines.append("Origenes usados:")
    lines.append(f"- Fuente `contracts.ini`: `{source_value}`")
    lines.append(f"- Generado: `{payload['generated_at']}`")
    lines.append("")
    lines.append("Resumen:")
    lines.append(f"- Titulos con marcas `[BP]` o `[Rep]`: {len(title_rows)}")
    lines.append(f"- Descripciones con `Reputation Awarded`: {len(desc_with_rep)}")
    lines.append(f"- Descripciones con `Scenario Progress Points`: {len(desc_with_points)}")
    lines.append(f"- Descripciones con tiers `Awarded from ... variants`: {len(desc_with_tiers)}")
    lines.append(f"- Casos con `Multiple Blueprint Pools` o `Pool N`: {len(multi_pool_rows)}")
    lines.append("")
    lines.append("Clasificacion de contexto:")
    for classification, count in sorted(class_counts.items()):
        lines.append(f"- `{classification}`: {count}")
    lines.append("")

    lines.append("## Titles")
    lines.append("")
    lines.append("| Clave | `[BP]` | `*` | Rangos `Rep` |")
    lines.append("|---|---|---|---|")
    for key, bp_flag, bp_uncertain, rep_ranges in title_rows:
        lines.append(f"| `{key}` | `{'si' if bp_flag else 'no'}` | `{'si' if bp_uncertain else 'no'}` | `{rep_ranges}` |")
    lines.append("")

    lines.append("## Reputation Awarded")
    lines.append("")
    lines.append("| Clave | Valores |")
    lines.append("|---|---|")
    for key, awarded in desc_with_rep:
        lines.append(f"| `{key}` | `{awarded}` |")
    lines.append("")

    lines.append("## Scenario Progress Points")
    lines.append("")
    lines.append("| Clave | Valores |")
    lines.append("|---|---|")
    for key, points in desc_with_points:
        lines.append(f"| `{key}` | `{points}` |")
    lines.append("")

    lines.append("## Variant Tiers")
    lines.append("")
    lines.append("| Clave | Tiers |")
    lines.append("|---|---|")
    for key, tiers in desc_with_tiers:
        lines.append(f"| `{key}` | `{tiers}` |")
    lines.append("")

    lines.append("## Multiple Pools")
    lines.append("")
    lines.append("| Clave | Clasificacion | Pools locales | Headers |")
    lines.append("|---|---|---|---|")
    for key, classification, local_pools, pool_headers in multi_pool_rows:
        lines.append(f"| `{key}` | `{classification}` | `{local_pools}` | `{pool_headers}` |")
    lines.append("")

    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrae metadatos candidatos desde contracts.ini sin tocar la build."
    )
    parser.add_argument("--contracts", default=DEFAULT_CONTRACTS)
    parser.add_argument("--global-ini", default=str(DEFAULT_GLOBAL))
    parser.add_argument("--pools", default=str(DEFAULT_POOLS))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--report-output", default=str(DEFAULT_REPORT_OUTPUT))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    contracts_source = args.contracts
    global_ini_path = Path(args.global_ini).expanduser().resolve()
    pools_path = Path(args.pools).expanduser().resolve()
    json_output = Path(args.json_output).expanduser().resolve()
    report_output = Path(args.report_output).expanduser().resolve()

    contracts_map = load_contract_entries(contracts_source)
    global_map = read_ini_map(global_ini_path)
    _pools, _mission_pool_map, normalized_pool_map = load_pool_source(pools_path)
    payload = build_payload(
        contracts_map=contracts_map,
        global_map=global_map,
        normalized_pool_map=normalized_pool_map,
    )

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    build_markdown_report(payload=payload, source_value=contracts_source, report_output=report_output)

    print(f"JSON generado: {json_output}")
    print(f"Informe generado: {report_output}")
    print(f"Titulos con metadatos: {len(payload['titles'])}")
    print(f"Descripciones con metadatos: {len(payload['descriptions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
