from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Entry:
    key: str
    value: str


@dataclass(frozen=True)
class GlobalIniData:
    entries: list[Entry]
    mapping: dict[str, str]


@dataclass(frozen=True)
class MergeResult:
    entries: list[Entry]
    missing: list[Entry]
    missing_count: int
    total_count: int


REFERENCE_TOKEN_RE = re.compile(r"@([A-Za-z0-9_.,-]+)@")


def resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def read_global_ini(path: str | Path) -> GlobalIniData:
    absolute_path = resolve_path(path)
    if not absolute_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {absolute_path}")

    entries: list[Entry] = []
    mapping: dict[str, str] = {}

    for raw_line in absolute_path.read_text(encoding="utf-8-sig").splitlines():
        if not raw_line.strip():
            continue

        if raw_line.startswith((";", "#")):
            continue

        separator_index = raw_line.find("=")
        if separator_index < 0:
            continue

        key = raw_line[:separator_index]
        value = raw_line[separator_index + 1 :]
        entry = Entry(key=key, value=value)
        entries.append(entry)
        mapping[key] = value

    return GlobalIniData(entries=entries, mapping=mapping)


def write_global_ini(entries: Iterable[Entry], path: str | Path) -> None:
    absolute_path = resolve_path(path)
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"{entry.key}={entry.value}" for entry in entries]
    # Star Citizen expects the same physical file format as the extracted
    # original global.ini: UTF-8 with BOM, CRLF line endings, and a final EOL.
    with absolute_path.open("w", encoding="utf-8-sig", newline="") as file_handle:
        file_handle.write("\r\n".join(lines))
        file_handle.write("\r\n")


def resolve_reference_tokens(
    value: str,
    *,
    reference_map: dict[str, str],
    missing_tokens: set[str] | None = None,
) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        replacement = reference_map.get(key)
        if replacement is None:
            if missing_tokens is not None:
                missing_tokens.add(key)
            return match.group(0)
        return replacement

    return REFERENCE_TOKEN_RE.sub(replace, value)


def resolve_reference_map(
    mapping: dict[str, str],
    *,
    reference_map: dict[str, str],
) -> tuple[dict[str, str], set[str]]:
    resolved: dict[str, str] = {}
    missing_tokens: set[str] = set()

    for key, value in mapping.items():
        resolved[key] = resolve_reference_tokens(
            value,
            reference_map=reference_map,
            missing_tokens=missing_tokens,
        )

    return resolved, missing_tokens


def merge_translations(english_data: GlobalIniData, translation_map: dict[str, str]) -> MergeResult:
    merged_entries: list[Entry] = []
    missing_entries: list[Entry] = []

    for entry in english_data.entries:
        value = translation_map.get(entry.key, entry.value)
        if entry.key not in translation_map:
            missing_entries.append(entry)

        merged_entries.append(Entry(key=entry.key, value=value))

    return MergeResult(
        entries=merged_entries,
        missing=missing_entries,
        missing_count=len(missing_entries),
        total_count=len(english_data.entries),
    )


def _overlay_suffix(base_value: str, overlay_value: str) -> str:
    # Backward compatibility: old overlay files may still store the full
    # resulting text instead of just the suffix to append.
    if overlay_value.startswith(base_value):
        return overlay_value[len(base_value) :]
    return overlay_value


def apply_overlay(base_entries: Iterable[Entry], overlay_map: dict[str, str]) -> list[Entry]:
    result: list[Entry] = []

    for entry in base_entries:
        value = entry.value
        overlay_value = overlay_map.get(entry.key)
        if overlay_value is not None:
            value = f"{value}{_overlay_suffix(entry.value, overlay_value)}"

        result.append(Entry(key=entry.key, value=value))

    return result


def apply_replacement_overlay(base_entries: Iterable[Entry], overlay_map: dict[str, str]) -> list[Entry]:
    result: list[Entry] = []

    for entry in base_entries:
        value = overlay_map.get(entry.key, entry.value)
        result.append(Entry(key=entry.key, value=value))

    return result
