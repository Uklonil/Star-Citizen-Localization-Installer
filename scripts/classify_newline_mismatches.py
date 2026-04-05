from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from localization_tools import resolve_path


def load_mismatches(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Agrupa las claves con saltos de linea alterados por diferencia de recuento.")
    parser.add_argument("--input", default="dist/validation/placeholder-mismatches.json")
    parser.add_argument("--output", default="dist/validation/newline-deltas.txt")
    args = parser.parse_args()

    input_path = resolve_path(args.input)
    output_path = resolve_path(args.output)
    mismatches = load_mismatches(input_path)

    grouped: dict[int, list[str]] = defaultdict(list)
    counter: Counter[int] = Counter()

    for item in mismatches:
        english_count = list(item["english_tokens"]).count("\\n")
        candidate_count = list(item["candidate_tokens"]).count("\\n")
        if english_count == candidate_count:
            continue

        delta = candidate_count - english_count
        grouped[delta].append(str(item["key"]))
        counter[delta] += 1

    lines: list[str] = []
    lines.append("Claves con diferencias en numero de \\n")
    lines.append("")
    for delta, count in counter.most_common():
        lines.append(f"Delta {delta}: {count}")
    lines.append("")

    for delta, keys in sorted(grouped.items(), key=lambda item: (abs(item[0]), item[0]), reverse=True):
        lines.append(f"[Delta {delta}]")
        for key in keys[:80]:
            lines.append(f"- {key}")
        if len(keys) > 80:
            lines.append(f"... {len(keys) - 80} claves mas")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(lines))

    print(f"Reporte generado: {output_path}")
    for delta, count in counter.most_common():
        print(f"Delta {delta}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
