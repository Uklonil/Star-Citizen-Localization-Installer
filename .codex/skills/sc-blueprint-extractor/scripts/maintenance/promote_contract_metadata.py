from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import REPO_ROOT


DEFAULT_DISCOVERY_INPUT = REPO_ROOT / "data" / "starcitizen" / "reports" / "blueprints" / "contracts_metadata_candidates.json"
DEFAULT_OUTPUT = REPO_ROOT / "source" / "blueprints" / "contracts_metadata.json"
DEFAULT_REPORT = REPO_ROOT / "informes" / "CONTRACTS_METADATA_PROMOTION_REPORT.md"

DEFAULT_ALLOWED_CLASSIFICATIONS = {
    "already-covered",
    "new-tier-label-only",
    "new-metadata-only",
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_promoted_payload(
    *,
    discovery_payload: dict[str, object],
    source_path: Path,
    allowed_classifications: set[str],
) -> tuple[dict[str, object], dict[str, int]]:
    titles = discovery_payload.get("titles", {})
    descriptions = discovery_payload.get("descriptions", {})
    blueprint_context = discovery_payload.get("blueprint_context", {})

    if not isinstance(titles, dict) or not isinstance(descriptions, dict) or not isinstance(blueprint_context, dict):
        raise ValueError(f"Payload de discovery invalido: {source_path}")

    title_meta: dict[str, dict[str, object]] = {}
    description_meta: dict[str, dict[str, object]] = {}

    counts = {
        "titles_total": 0,
        "titles_promoted": 0,
        "descriptions_total": 0,
        "descriptions_promoted": 0,
        "descriptions_skipped": 0,
    }

    for key, raw_meta in sorted(titles.items(), key=lambda item: item[0].lower()):
        if not isinstance(raw_meta, dict):
            continue
        counts["titles_total"] += 1
        title_meta[key] = {
            "blueprint_flag": bool(raw_meta.get("blueprint_flag")),
            "blueprint_flag_uncertain": bool(raw_meta.get("blueprint_flag_uncertain")),
            "rep_ranges": list(raw_meta.get("rep_ranges", [])),
        }
        counts["titles_promoted"] += 1

    for key, raw_meta in sorted(descriptions.items(), key=lambda item: item[0].lower()):
        if not isinstance(raw_meta, dict):
            continue
        counts["descriptions_total"] += 1

        context = blueprint_context.get(key, {})
        classification = context.get("classification") if isinstance(context, dict) else None
        if classification not in allowed_classifications:
            counts["descriptions_skipped"] += 1
            continue

        description_meta[key] = {
            "classification": classification,
            "reputation_awarded": list(raw_meta.get("reputation_awarded", [])),
            "scenario_progress_points": list(raw_meta.get("scenario_progress_points", [])),
            "tier_labels": list(raw_meta.get("blueprint_variant_tiers", [])),
            "has_potential_blueprints_block": bool(raw_meta.get("has_potential_blueprints_block")),
            "has_multiple_blueprint_pools": bool(raw_meta.get("has_multiple_blueprint_pools")),
            "local_pool_ids": list(context.get("local_pool_ids", [])) if isinstance(context, dict) else [],
        }
        counts["descriptions_promoted"] += 1

    payload = {
        "version": 1,
        "generated_from": {
            "discovery": str(source_path.relative_to(REPO_ROOT).as_posix()),
        },
        "notes": [
            "Fuente versionada de metadatos derivados de contracts.ini de StarStrings.",
            "No participa en la build hasta integracion explicita.",
            "Se separa de pools.json para no mezclar recompensas visibles con reputacion, tiers y puntos de escenario.",
            "Se excluyen clasificaciones de subpools complejos hasta revision manual.",
        ],
        "title_meta": title_meta,
        "description_meta": description_meta,
    }
    return payload, counts


def build_report(
    *,
    output_path: Path,
    source_path: Path,
    target_path: Path,
    allowed_classifications: set[str],
    counts: dict[str, int],
    payload: dict[str, object],
) -> None:
    description_meta = payload["description_meta"]
    lines: list[str] = []
    lines.append("# Contracts Metadata Promotion Report")
    lines.append("")
    lines.append("Origenes usados:")
    lines.append(f"- Discovery: `{source_path.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- Destino: `{target_path.relative_to(REPO_ROOT).as_posix()}`")
    lines.append("")
    lines.append("Clasificaciones promovidas:")
    for classification in sorted(allowed_classifications):
        lines.append(f"- `{classification}`")
    lines.append("")
    lines.append("Resumen:")
    lines.append(f"- Titulos discovery: {counts['titles_total']}")
    lines.append(f"- Titulos promovidos: {counts['titles_promoted']}")
    lines.append(f"- Descripciones discovery: {counts['descriptions_total']}")
    lines.append(f"- Descripciones promovidas: {counts['descriptions_promoted']}")
    lines.append(f"- Descripciones descartadas: {counts['descriptions_skipped']}")
    lines.append("")
    lines.append("## Muestra de descripciones promovidas")
    lines.append("")
    lines.append("| Clave | Clasificacion | Tiers | Reputacion | Scenario Points | Pools locales |")
    lines.append("|---|---|---|---|---|---|")
    shown = 0
    for key, meta in sorted(description_meta.items(), key=lambda item: item[0].lower()):
        tiers = ", ".join(meta.get("tier_labels", []))
        reputation = ", ".join(meta.get("reputation_awarded", []))
        points = ", ".join(meta.get("scenario_progress_points", []))
        pools = ", ".join(meta.get("local_pool_ids", []))
        lines.append(
            f"| `{key}` | `{meta.get('classification', '')}` | `{tiers}` | `{reputation}` | `{points}` | `{pools}` |"
        )
        shown += 1
        if shown >= 40:
            break
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promociona metadatos de contratos desde el artefacto de discovery a source/blueprints/contracts_metadata.json."
    )
    parser.add_argument("--discovery-input", default=str(DEFAULT_DISCOVERY_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report-output", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--allow-classification",
        action="append",
        dest="allowed_classifications",
        help="Clasificacion permitida. Repetible. Por defecto: already-covered, new-tier-label-only, new-metadata-only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    source_path = Path(args.discovery_input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    report_output = Path(args.report_output).expanduser().resolve()
    allowed_classifications = set(args.allowed_classifications or DEFAULT_ALLOWED_CLASSIFICATIONS)

    discovery_payload = load_json(source_path)
    promoted_payload, counts = build_promoted_payload(
        discovery_payload=discovery_payload,
        source_path=source_path,
        allowed_classifications=allowed_classifications,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(promoted_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_report(
        output_path=report_output,
        source_path=source_path,
        target_path=output_path,
        allowed_classifications=allowed_classifications,
        counts=counts,
        payload=promoted_payload,
    )

    print(f"Fuente promovida: {output_path}")
    print(f"Informe generado: {report_output}")
    print(f"Titulos promovidos: {counts['titles_promoted']}")
    print(f"Descripciones promovidas: {counts['descriptions_promoted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
