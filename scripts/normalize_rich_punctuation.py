from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

REPLACEMENTS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u00a0": " ",
    "\u202f": " ",
    "\u2013": "-",
    "\u2014": "-",
}


@dataclass(frozen=True)
class FileResult:
    path: Path
    changed_lines: int
    replacement_count: int


def resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def normalize_text(text: str) -> tuple[str, int]:
    normalized = text
    replacements = 0
    for source, target in REPLACEMENTS.items():
        count = normalized.count(source)
        if count:
            normalized = normalized.replace(source, target)
            replacements += count
    return normalized, replacements


def normalize_file(path: Path) -> FileResult:
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    original = raw.decode("utf-8-sig")
    normalized, replacement_count = normalize_text(original)
    changed_lines = sum(
        1 for original_line, normalized_line in zip(original.splitlines(), normalized.splitlines()) if original_line != normalized_line
    )

    if normalized != original or has_bom:
        encoding = "utf-8-sig" if has_bom else "utf-8"
        with path.open("w", encoding=encoding, newline="") as file_handle:
            file_handle.write(normalized)

    return FileResult(path=path, changed_lines=changed_lines, replacement_count=replacement_count)


def default_language_files(language_code: str) -> list[Path]:
    language_root = REPO_ROOT / "source" / "languages" / language_code
    return [
        language_root / "translation.ini",
        language_root / "overlays" / "modified_global.ini",
        language_root / "overlays" / "components.ini",
        language_root / "overlays" / "blueprints.ini",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normaliza puntuacion Unicode problematica en memorias de traduccion y overlays."
    )
    parser.add_argument("--language", help="Codigo de idioma bajo source/languages/<codigo>.")
    parser.add_argument("--file", action="append", help="Archivo concreto a normalizar. Puede repetirse.")
    args = parser.parse_args()

    targets: list[Path] = []
    if args.language:
        targets.extend(default_language_files(args.language))
    if args.file:
        targets.extend(resolve_path(path) for path in args.file)

    if not targets:
        raise SystemExit("Indica --language o al menos un --file.")

    unique_targets: list[Path] = []
    seen: set[Path] = set()
    for path in targets:
        resolved = resolve_path(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_targets.append(resolved)

    total_changed_lines = 0
    total_replacements = 0
    for path in unique_targets:
        if not path.is_file():
            raise FileNotFoundError(f"No existe el archivo: {path}")
        result = normalize_file(path)
        total_changed_lines += result.changed_lines
        total_replacements += result.replacement_count
        print(
            f"{result.path}: lineas cambiadas={result.changed_lines}, reemplazos={result.replacement_count}"
        )

    print(f"Total lineas cambiadas: {total_changed_lines}")
    print(f"Total reemplazos: {total_replacements}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
