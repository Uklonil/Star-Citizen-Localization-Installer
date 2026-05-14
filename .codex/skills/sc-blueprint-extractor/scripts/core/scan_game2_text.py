from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse
import json
import re

from dcb_text_support import split_strings_with_offsets


TITLE_DESC_KEY_RE = re.compile(rb"[A-Za-z0-9_.:-]+_(?:title|desc)(?:_[A-Za-z0-9_.:-]+)?")
CONTRACT_RE = re.compile(rb"(?:ContractGenerator\.[A-Za-z0-9_.:-]+|contractgenerator/[A-Za-z0-9_./:-]+\.xml)", re.IGNORECASE)
MISSIONDATA_RE = re.compile(rb"missiondata/[A-Za-z0-9_./:-]+\.xml", re.IGNORECASE)
POOL_RE = re.compile(rb"BP_MISSIONREWARD_[A-Za-z0-9_]+")
ITEM_RE = re.compile(rb"item_[A-Za-z0-9_]+")


def read_ini_keys(path: Path) -> set[str]:
    keys: set[str] = set()

    if not path.exists():
        return keys

    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        stripped = raw_line.strip()

        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue

        if "=" not in raw_line:
            continue

        key, _value = raw_line.split("=", 1)
        key = key.strip()

        if key:
            keys.add(key)

    return keys


def decode_token(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def find_tokens(data: bytes, pattern: re.Pattern[bytes]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}

    for match in pattern.finditer(data):
        token = decode_token(match.group(0))
        found.setdefault(token, []).append(match.start())

    return found


def find_tokens_in_strings(strings: list[tuple[int, str]], pattern: re.Pattern[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for offset, value in strings:
        for match in pattern.finditer(value):
            token = match.group(0)
            found.setdefault(token, []).append(offset + match.start())
    return found


def nearest_tokens(
    positions: list[int],
    token_map: dict[str, list[int]],
    window: int,
) -> list[str]:
    results: set[str] = set()

    for position in positions:
        start = position - window
        end = position + window

        for token, token_positions in token_map.items():
            if any(start <= token_position <= end for token_position in token_positions):
                results.add(token)

    return sorted(results)


def main() -> None:
    args = parse_args()

    game2 = Path(args.game2)
    global_ini = Path(args.global_ini)
    template = Path(args.template)
    pools = Path(args.pools)
    data_report = Path(args.data_report)
    md_report = Path(args.md_report)

    if not game2.exists():
        raise SystemExit(f"Game2.dcb not found: {game2}")

    data = game2.read_bytes()
    strings = split_strings_with_offsets(data)

    global_keys = read_ini_keys(global_ini)
    template_keys = read_ini_keys(template)

    title_desc_tokens = find_tokens(data, TITLE_DESC_KEY_RE)
    contract_tokens = find_tokens(data, CONTRACT_RE)
    missiondata_tokens = find_tokens(data, MISSIONDATA_RE)
    pool_tokens = find_tokens(data, POOL_RE)
    item_tokens = find_tokens(data, ITEM_RE)
    if not contract_tokens and strings:
        contract_tokens = find_tokens_in_strings(strings, re.compile(CONTRACT_RE.pattern.decode("ascii"), re.IGNORECASE))
    if not missiondata_tokens and strings:
        missiondata_tokens = find_tokens_in_strings(strings, re.compile(MISSIONDATA_RE.pattern.decode("ascii"), re.IGNORECASE))

    title_desc_in_global = sorted(key for key in title_desc_tokens if key in global_keys)
    title_desc_missing_from_template = sorted(
        key for key in title_desc_in_global
        if key not in template_keys
    )

    candidates = []

    for key in title_desc_missing_from_template:
        positions = title_desc_tokens[key]

        candidates.append({
            "key": key,
            "positions": positions[:10],
            "contracts_nearby": nearest_tokens(positions, contract_tokens, args.window),
            "missiondata_nearby": nearest_tokens(positions, missiondata_tokens, args.window),
            "pools_nearby": nearest_tokens(positions, pool_tokens, args.window),
            "items_nearby": nearest_tokens(positions, item_tokens, args.window)[:50],
        })

    result = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "game2": str(game2),
        "global_ini": str(global_ini),
        "template": str(template),
        "pools": str(pools),
        "window": args.window,
        "counts": {
            "global_keys": len(global_keys),
            "template_keys": len(template_keys),
            "title_desc_tokens_in_game2": len(title_desc_tokens),
            "title_desc_tokens_in_global": len(title_desc_in_global),
            "title_desc_missing_from_template": len(title_desc_missing_from_template),
            "contract_tokens": len(contract_tokens),
            "missiondata_tokens": len(missiondata_tokens),
            "pool_tokens": len(pool_tokens),
            "item_tokens": len(item_tokens),
        },
        "tokens": {
            "contracts": sorted(contract_tokens.keys()),
            "missiondata": sorted(missiondata_tokens.keys()),
            "pools": sorted(pool_tokens.keys()),
        },
        "candidates": candidates,
    }

    data_report.parent.mkdir(parents=True, exist_ok=True)
    data_report.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    write_markdown_report(
        md_report=md_report,
        result=result,
        starbreaker=args.starbreaker,
        p4k=args.p4k,
        data_report=data_report,
    )

    print("OK")
    print(f"Candidates: {len(candidates)}")
    print(f"Data report: {data_report}")
    print(f"Markdown report: {md_report}")


def write_markdown_report(
    md_report: Path,
    result: dict,
    starbreaker: str,
    p4k: str,
    data_report: Path,
) -> None:
    counts = result["counts"]
    candidates = result["candidates"]

    lines = [
        "# Blueprints Extraction Report",
        "",
        f"- Timestamp: `{result['timestamp']}`",
        f"- StarBreaker: `{starbreaker}`",
        f"- Data.p4k: `{p4k}`",
        f"- Game2.dcb: `{result['game2']}`",
        f"- Data report: `{data_report}`",
        "",
        "## Counts",
        "",
        f"- Global keys: `{counts['global_keys']}`",
        f"- Template keys: `{counts['template_keys']}`",
        f"- Title/desc tokens in Game2.dcb: `{counts['title_desc_tokens_in_game2']}`",
        f"- Title/desc tokens also in global.ini: `{counts['title_desc_tokens_in_global']}`",
        f"- Title/desc keys missing from blueprint template: `{counts['title_desc_missing_from_template']}`",
        f"- Contract tokens: `{counts['contract_tokens']}`",
        f"- Missiondata tokens: `{counts['missiondata_tokens']}`",
        f"- Pool tokens: `{counts['pool_tokens']}`",
        f"- Item tokens: `{counts['item_tokens']}`",
        "",
        "## Candidate keys",
        "",
    ]

    if not candidates:
        lines.append("No candidate keys found.")
    else:
        for candidate in candidates[:300]:
            lines.append(f"### `{candidate['key']}`")
            lines.append("")
            lines.append(f"- Contracts nearby: `{', '.join(candidate['contracts_nearby']) or 'none'}`")
            lines.append(f"- Missiondata nearby: `{', '.join(candidate['missiondata_nearby']) or 'none'}`")
            lines.append(f"- Pools nearby: `{', '.join(candidate['pools_nearby']) or 'none'}`")
            lines.append(f"- Nearby item refs: `{len(candidate['items_nearby'])}`")
            lines.append("")

        if len(candidates) > 300:
            lines.append(f"... truncated in Markdown report. Full data report contains `{len(candidates)}` candidates.")
            lines.append("")

    lines.extend([
        "## Recommended next actions",
        "",
        "1. Review candidates with nearby contract and missiondata links first.",
        "2. Run or update `.codex/skills/sc-blueprint-extractor/scripts/review/infer_blueprint_pools_from_contracts.py` if available.",
        "3. Only apply strict inferences to `source/blueprints/blueprints_template.ini` after review.",
        "4. Regenerate the blueprint overlay and run a distribution build.",
        "",
    ])

    md_report.parent.mkdir(parents=True, exist_ok=True)
    md_report.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Game2.dcb binary text windows for mission, contract, missiondata, item and blueprint pool candidates."
    )
    parser.add_argument("--game2", required=True)
    parser.add_argument("--global-ini", default="input/current/global.ini")
    parser.add_argument("--template", default="source/blueprints/blueprints_template.ini")
    parser.add_argument("--pools", default="source/blueprints/pools.json")
    parser.add_argument("--data-report", default="/data/starcitizen/reports/blueprints/game2-text-scan.json")
    parser.add_argument("--md-report", default="informes/BLUEPRINTS_EXTRACTION_REPORT.md")
    parser.add_argument("--starbreaker", default="tools/starbreaker.exe")
    parser.add_argument("--p4k", default="")
    parser.add_argument("--window", type=int, default=12000)
    return parser.parse_args()


if __name__ == "__main__":
    main()
