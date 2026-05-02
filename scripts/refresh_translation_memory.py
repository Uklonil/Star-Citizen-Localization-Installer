from __future__ import annotations

import argparse
from pathlib import Path

from build_distributions import extract_tokens
from localization_tools import Entry, read_global_ini, resolve_path, write_global_ini


def clip(value: str, limit: int = 200) -> str:
    normalized = value.replace("\n", "\\n")
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def write_report(
    *,
    report_path: Path,
    output_path: Path,
    added_keys: list[str],
    unknown_keys: list[str],
    token_reset_keys: list[str],
) -> None:
    lines: list[str] = [
        f"Destino actualizado: {output_path}",
        f"Claves nuevas rellenadas con ingles: {len(added_keys)}",
        f"Claves obsoletas eliminadas: {len(unknown_keys)}",
        f"Claves reiniciadas a ingles por integridad de tokens: {len(token_reset_keys)}",
        "",
    ]

    sections = (
        ("Claves nuevas", added_keys),
        ("Claves obsoletas", unknown_keys),
        ("Claves reiniciadas por integridad", token_reset_keys),
    )
    for title, keys in sections:
        lines.append(f"{title}:")
        if keys:
            lines.extend(keys)
        else:
            lines.append("(ninguna)")
        lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(lines))


def write_changed_english_report(
    *,
    report_path: Path,
    previous_english_path: Path,
    current_english_path: Path,
    translation_path: Path,
) -> None:
    previous_english_data = read_global_ini(previous_english_path)
    current_english_data = read_global_ini(current_english_path)
    translation_data = read_global_ini(translation_path)

    changed_keys = [
        entry.key
        for entry in current_english_data.entries
        if entry.key in previous_english_data.mapping
        and previous_english_data.mapping[entry.key] != entry.value
    ]

    lines = [
        f"Origen ingles anterior: {previous_english_path}",
        f"Origen ingles actual: {current_english_path}",
        f"Memoria revisada: {translation_path}",
        f"Claves cuyo texto ingles ha cambiado respecto al origen anterior: {len(changed_keys)}",
        "",
    ]

    for key in changed_keys:
        lines.extend(
            [
                f"Clave: {key}",
                f"Ingles anterior: {clip(previous_english_data.mapping[key])}",
                f"Ingles actual: {clip(current_english_data.mapping[key])}",
                f"Traduccion actual: {clip(translation_data.mapping.get(key, '<NO_ENCONTRADO>'))}",
                "",
            ]
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Realinea translation.ini con el global.ini actual, preservando traducciones "
            "validas por clave y rellenando con ingles las claves nuevas o con tokens rotos."
        )
    )
    parser.add_argument("--english-global-ini", default="input/current/global.ini")
    parser.add_argument("--translation-memory", default="source/languages/es-es/translation.ini")
    parser.add_argument("--output")
    parser.add_argument("--report", default="informes/TRANSLATION_MEMORY_REFRESH_REPORT.md")
    parser.add_argument(
        "--previous-english-global-ini",
        help="Ruta a un global.ini ingles anterior para generar un informe de claves modificadas.",
    )
    parser.add_argument(
        "--changed-report",
        default="informes/ENGLISH_CHANGED_KEYS_REVIEW.md",
        help="Informe de claves cuyo ingles ha cambiado respecto al origen anterior.",
    )
    args = parser.parse_args()

    english_path = resolve_path(args.english_global_ini)
    translation_path = resolve_path(args.translation_memory)
    output_path = resolve_path(args.output) if args.output else translation_path
    report_path = resolve_path(args.report)
    changed_report_path = resolve_path(args.changed_report)

    english_data = read_global_ini(english_path)
    translation_data = read_global_ini(translation_path)

    translation_map = translation_data.mapping
    added_keys: list[str] = []
    token_reset_keys: list[str] = []

    refreshed_entries: list[Entry] = []
    for entry in english_data.entries:
        translated_value = translation_map.get(entry.key)
        if translated_value is None:
            added_keys.append(entry.key)
            refreshed_entries.append(entry)
            continue

        if extract_tokens(translated_value) != extract_tokens(entry.value):
            token_reset_keys.append(entry.key)
            refreshed_entries.append(entry)
            continue

        refreshed_entries.append(Entry(key=entry.key, value=translated_value))

    unknown_keys = [entry.key for entry in translation_data.entries if entry.key not in english_data.mapping]

    write_global_ini(refreshed_entries, output_path)
    write_report(
        report_path=report_path,
        output_path=output_path,
        added_keys=added_keys,
        unknown_keys=unknown_keys,
        token_reset_keys=token_reset_keys,
    )

    if args.previous_english_global_ini:
        write_changed_english_report(
            report_path=changed_report_path,
            previous_english_path=resolve_path(args.previous_english_global_ini),
            current_english_path=english_path,
            translation_path=output_path,
        )

    print(f"Memoria actualizada: {output_path}")
    print(f"Claves nuevas rellenadas con ingles: {len(added_keys)}")
    print(f"Claves obsoletas eliminadas: {len(unknown_keys)}")
    print(f"Claves reiniciadas por tokens: {len(token_reset_keys)}")
    print(f"Informe: {report_path}")
    if args.previous_english_global_ini:
        print(f"Informe de claves cambiadas: {changed_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
