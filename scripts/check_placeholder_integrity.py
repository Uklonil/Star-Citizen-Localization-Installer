from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_distributions import extract_tokens
from localization_tools import read_global_ini, resolve_path


def clip(value: str, limit: int = 220) -> str:
    normalized = value.replace("\n", "\\n")
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def find_token_mismatches(*, english_map: dict[str, str], candidate_map: dict[str, str]) -> list[dict[str, object]]:
    mismatches: list[dict[str, object]] = []
    for key, candidate_value in candidate_map.items():
        english_value = english_map.get(key)
        if english_value is None:
            continue

        english_tokens = extract_tokens(english_value)
        candidate_tokens = extract_tokens(candidate_value)
        if english_tokens == candidate_tokens:
            continue

        mismatches.append(
            {
                "key": key,
                "english_tokens": english_tokens,
                "candidate_tokens": candidate_tokens,
                "english_value": english_value,
                "candidate_value": candidate_value,
            }
        )
    return mismatches


def write_text_report(path: Path, mismatches: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"Claves con placeholders o markup alterados: {len(mismatches)}")
    lines.append("")

    for item in mismatches:
        lines.extend(
            [
                f"Clave: {item['key']}",
                f"Tokens origen: {item['english_tokens']}",
                f"Tokens traduccion: {item['candidate_tokens']}",
                f"Origen: {clip(str(item['english_value']))}",
                f"Traduccion: {clip(str(item['candidate_value']))}",
                "",
            ]
        )

    with path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(lines))


def write_json_report(path: Path, mismatches: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write(json.dumps(mismatches, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detecta claves cuya traduccion altera placeholders, escapes o markup respecto al global.ini ingles."
    )
    parser.add_argument("--english-global-ini", default="input/current/global.ini")
    parser.add_argument("--translation-memory", default="source/translations/base-spanish.ini")
    parser.add_argument("--output-dir", default="dist/validation")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Numero de resultados a mostrar por consola. El reporte completo se guarda en disco.",
    )
    args = parser.parse_args()

    english_absolute = resolve_path(args.english_global_ini)
    translation_absolute = resolve_path(args.translation_memory)
    output_dir = resolve_path(args.output_dir)

    english_data = read_global_ini(english_absolute)
    translation_data = read_global_ini(translation_absolute)
    mismatches = find_token_mismatches(
        english_map=english_data.mapping,
        candidate_map=translation_data.mapping,
    )

    text_report = output_dir / "placeholder-mismatches.txt"
    json_report = output_dir / "placeholder-mismatches.json"
    write_text_report(text_report, mismatches)
    write_json_report(json_report, mismatches)

    print(f"Total de claves con problemas: {len(mismatches)}")
    print(f"Reporte texto: {text_report}")
    print(f"Reporte JSON: {json_report}")

    for item in mismatches[: args.limit]:
        print(f"- {item['key']}")
        print(f"  origen: {item['english_tokens']}")
        print(f"  traduccion: {item['candidate_tokens']}")

    if len(mismatches) > args.limit:
        print(f"... {len(mismatches) - args.limit} claves mas en el reporte completo.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
