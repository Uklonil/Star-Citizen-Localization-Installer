from __future__ import annotations

import argparse
from pathlib import Path
import sys

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import REPO_ROOT


DEFAULT_INPUT = REPO_ROOT / "informes" / "BLUEPRINTS_NEW_MISSION_CANDIDATES.md"
DEFAULT_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_NEW_MISSION_CANDIDATES_SHORTLIST.md"

EXCLUDED_TOKENS = (
    "Certification",
    "ReputationJournal",
    "RepUI",
    "Journal",
)


def should_keep(title_key: str, desc_key: str) -> bool:
    if desc_key == "-":
        return False
    haystack = f"{title_key} {desc_key}"
    return not any(token.lower() in haystack.lower() for token in EXCLUDED_TOKENS)


def parse_rows(lines: list[str]) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for raw_line in lines:
        if not raw_line.startswith("| `"):
            continue
        parts = [part.strip() for part in raw_line.strip().strip("|").split("|")]
        if len(parts) != 5:
            continue
        rows.append(tuple(parts))  # type: ignore[arg-type]
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un shortlist filtrado de misiones nuevas candidatas a blueprints.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    lines = input_path.read_text(encoding="utf-8").splitlines()
    rows = parse_rows(lines)
    filtered = [row for row in rows if should_keep(row[1].strip("`"), row[2].strip("`"))]
    families = {row[0] for row in filtered}

    out_lines = [
        "# Shortlist de misiones nuevas candidatas a blueprints",
        "",
        "Criterio:",
        f"- Sale del informe `{input_path.name}`.",
        "- Solo incluye entradas con `desc` presente en `global.ini`.",
        "- Excluye certificaciones, reputation journals y otros textos de progresion no jugables.",
        "",
        "Resumen:",
        f"- Entradas shortlist: {len(filtered)}",
        f"- Familias shortlist: {len(families)}",
        "",
        "| Familia | Clave `title` | Clave `desc` | Titulo ingles | Pools candidatas |",
        "|---|---|---|---|---|",
    ]
    out_lines.extend(f"| {' | '.join(row)} |" for row in filtered)
    out_lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(out_lines))

    print(f"Shortlist generada: {output_path}")
    print(f"Entradas: {len(filtered)}")
    print(f"Familias: {len(families)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
