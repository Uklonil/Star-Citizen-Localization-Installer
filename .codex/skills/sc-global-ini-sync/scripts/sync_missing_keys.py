from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse


DEFAULT_SOURCE = Path("input/current/global.ini")
DEFAULT_TRANSLATION = Path("source/languages/es-es/translation.ini")
DEFAULT_REPORT = Path("informes/global-ini-sync-report.md")


@dataclass
class IniEntry:
    key: str
    value: str
    line_number: int


@dataclass
class ParsedIni:
    entries: dict[str, IniEntry]
    duplicates: dict[str, list[int]]
    lines: list[str]


def read_text_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace").splitlines()


def parse_ini_like(path: Path) -> ParsedIni:
    lines = read_text_lines(path)
    entries: dict[str, IniEntry] = {}
    duplicates: dict[str, list[int]] = {}

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("#") or stripped.startswith(";"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()

        if not key:
            continue

        if key in entries:
            duplicates.setdefault(key, [entries[key].line_number]).append(index)
            continue

        entries[key] = IniEntry(
            key=key,
            value=value,
            line_number=index,
        )

    return ParsedIni(entries=entries, duplicates=duplicates, lines=lines)


def append_missing_keys(
    source: Path,
    translation: Path,
    report: Path,
    block_label: str,
    dry_run: bool,
) -> int:
    source_ini = parse_ini_like(source)
    translation_ini = parse_ini_like(translation)

    missing_keys = [
        key
        for key in source_ini.entries.keys()
        if key not in translation_ini.entries
    ]

    translation_count_before = len(translation_ini.entries)
    translation_count_after = translation_count_before + len(missing_keys)

    if missing_keys and not dry_run:
        lines = list(translation_ini.lines)

        if lines and lines[-1].strip() != "":
            lines.append("")

        lines.extend([
            "",
            "; ============================================================",
            f"; Added by sc-global-ini-sync on {datetime.now().isoformat(timespec='seconds')}",
            f"; Block: {block_label}",
            "; Values copied from input/current/global.ini before translation",
            "; ============================================================",
        ])

        for key in missing_keys:
            value = source_ini.entries[key].value
            lines.append(f"{key}={value}")

        translation.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report.parent.mkdir(parents=True, exist_ok=True)

    report.write_text(
        "\n".join([
            "# Global.ini Sync Report",
            "",
            f"- Missing keys added: {len(missing_keys)}",
            f"- Translation count before: {translation_count_before}",
            f"- Translation count after: {translation_count_after}",
        ]) + "\n",
        encoding="utf-8"
    )

    return len(missing_keys)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--translation", default=str(DEFAULT_TRANSLATION))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--block-label", default="patch-sync")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    added = append_missing_keys(
        source=Path(args.source),
        translation=Path(args.translation),
        report=Path(args.report),
        block_label=args.block_label,
        dry_run=args.dry_run,
    )

    print("OK")
    print(f"Added keys: {added}")


if __name__ == "__main__":
    main()
