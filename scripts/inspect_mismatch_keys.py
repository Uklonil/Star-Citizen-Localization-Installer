from __future__ import annotations

import argparse
from pathlib import Path

from build_distributions import extract_tokens
from localization_tools import read_global_ini, resolve_path


def load_keys(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_line_number(path: Path, key: str) -> int | None:
    for index, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if raw_line.startswith(f"{key}="):
            return index
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspecciona claves concretas mostrando origen, traduccion y tokens.")
    parser.add_argument("--keys-file", required=True)
    parser.add_argument("--english-global-ini", default="input/current/global.ini")
    parser.add_argument("--translation-memory", default="source/languages/es-es/translation.ini")
    parser.add_argument("--output", default="dist/validation/inspected-mismatches.txt")
    args = parser.parse_args()

    keys_file = resolve_path(args.keys_file)
    english_path = resolve_path(args.english_global_ini)
    translation_path = resolve_path(args.translation_memory)
    output_path = resolve_path(args.output)

    english_data = read_global_ini(english_path)
    translation_data = read_global_ini(translation_path)
    keys = load_keys(keys_file)

    lines: list[str] = []
    for key in keys:
        english_value = english_data.mapping.get(key, "<NO_ENCONTRADO>")
        candidate_value = translation_data.mapping.get(key, "<NO_ENCONTRADO>")
        english_tokens = extract_tokens(english_value) if english_value != "<NO_ENCONTRADO>" else []
        candidate_tokens = extract_tokens(candidate_value) if candidate_value != "<NO_ENCONTRADO>" else []
        line_number = find_line_number(translation_path, key)

        lines.extend(
            [
                f"Clave: {key}",
                f"Linea {translation_path.name}: {line_number}",
                f"Tokens origen: {english_tokens}",
                f"Tokens traduccion: {candidate_tokens}",
                f"Origen: {english_value}",
                f"Traduccion: {candidate_value}",
                "",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(lines))

    print(f"Reporte generado: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
