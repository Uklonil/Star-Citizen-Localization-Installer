from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.language_support import (
    SourceLanguage,
    discover_source_languages,
    find_source_language,
    write_staged_language_metadata,
)
from localization_tools import (
    apply_overlay,
    apply_replacement_overlay,
    merge_translations,
    normalize_global_ini_data,
    read_global_ini,
    resolve_reference_map,
    resolve_path,
    write_global_ini,
)

PLACEHOLDER_RE = re.compile(
    r"(%(?:\d+\$)?[sdif])"
    r"|(\{(?:\d+|[a-z_][a-z0-9_]*)\})"
    r"|(\\n|\\t|\\r|\\\")"
    r"|(\[\[.*?\]\])"
    r"|(</?EM[1-4]>)"
)


def extract_tokens(value: str) -> list[str]:
    matches = PLACEHOLDER_RE.findall(value)
    return [token for group in matches for token in group if token]


def contains_subsequence(tokens: list[str], expected: list[str]) -> bool:
    if not expected:
        return True

    cursor = 0
    for token in tokens:
        if token == expected[cursor]:
            cursor += 1
            if cursor == len(expected):
                return True

    return False


def validate_reference_map(
    *,
    english_map: dict[str, str],
    candidate_map: dict[str, str],
    label: str,
    validate_tokens: bool = True,
    allow_added_tokens: bool = False,
) -> list[str]:
    errors: list[str] = []

    unknown_keys = sorted(set(candidate_map) - set(english_map))
    if unknown_keys:
        sample = ", ".join(unknown_keys[:10])
        errors.append(
            f"{label}: contains {len(unknown_keys)} keys that do not exist in the English global.ini. "
            f"Examples: {sample}"
        )

    for key, candidate_value in candidate_map.items():
        english_value = english_map.get(key)
        if english_value is None:
            continue

        if not validate_tokens:
            continue

        english_tokens = extract_tokens(english_value)
        candidate_tokens = extract_tokens(candidate_value)
        tokens_valid = (
            contains_subsequence(candidate_tokens, english_tokens)
            if allow_added_tokens
            else candidate_tokens == english_tokens
        )
        if not tokens_valid:
            errors.append(f"{label}: placeholders or markup altered in key {key}")

    return errors


def validate_output_entries(*, english_entries, output_entries, label: str) -> list[str]:
    errors: list[str] = []
    english_entries = list(english_entries)
    output_entries = list(output_entries)

    if len(english_entries) != len(output_entries):
        errors.append(
            f"{label}: the number of entries does not match the source "
            f"({len(output_entries)} vs {len(english_entries)})"
        )
        return errors

    for index, (english_entry, output_entry) in enumerate(zip(english_entries, output_entries), start=1):
        if english_entry.key != output_entry.key:
            errors.append(
                f"{label}: change of key or order in line {index}: "
                f"{english_entry.key} -> {output_entry.key}"
            )
            continue

        english_tokens = extract_tokens(english_entry.value)
        output_tokens = extract_tokens(output_entry.value)
        if not contains_subsequence(output_tokens, english_tokens):
            errors.append(f"{label}: placeholders o markup alterados en la clave {english_entry.key}")

    return errors


def write_user_cfg(*, path: Path, game_language: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write(f"g_language = {game_language}\n")


def create_package(
    *,
    package_root: Path,
    zip_path: Path,
    entries,
    game_language: str,
    user_cfg_source: Path | None,
) -> None:
    global_ini_path = package_root / "data" / "Localization" / game_language / "global.ini"
    write_global_ini(entries=entries, path=global_ini_path)
    user_cfg_path = package_root / "user.cfg"
    if user_cfg_source is not None and user_cfg_source.is_file():
        shutil.copy2(user_cfg_source, user_cfg_path)
    else:
        write_user_cfg(path=user_cfg_path, game_language=game_language)

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in package_root.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(package_root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generates ZIP distributions for localization by language.")
    parser.add_argument("--english-global-ini", default="input/current/global.ini")
    parser.add_argument("--language", help="Language code to compile. If omitted, compiles all configured languages.")
    parser.add_argument("--translation-memory")
    parser.add_argument("--modified-overlay")
    parser.add_argument("--components-overlay")
    parser.add_argument("--blueprints-overlay")
    parser.add_argument("--user-cfg")
    parser.add_argument("--version", default="dev")
    parser.add_argument("--output-root", default="dist")
    parser.add_argument(
        "--allow-empty-translation-memory",
        action="store_true",
        help="Allows generating packages even if the master memory does not provide any base translations.",
    )
    args = parser.parse_args()

    english_absolute = resolve_path(args.english_global_ini)
    output_absolute = resolve_path(args.output_root)

    if not english_absolute.exists():
        raise FileNotFoundError(f"Required file missing: {english_absolute}")

    english_data = normalize_global_ini_data(read_global_ini(english_absolute))
    version_root = output_absolute / args.version
    packages_root = version_root / "packages"
    staging_root = version_root / "staging"
    reports_root = version_root / "reports"

    for directory in (packages_root, staging_root, reports_root):
        directory.mkdir(parents=True, exist_ok=True)

    languages = [find_source_language(resolve_path("."), args.language)] if args.language else discover_source_languages(resolve_path("."))

    summary_lines = [f"Version: {args.version}"]
    total_missing = 0

    for language in languages:
        translation_absolute = resolve_path(args.translation_memory) if args.translation_memory else language.translation_memory
        modified_absolute = resolve_path(args.modified_overlay) if args.modified_overlay else language.modified_overlay
        components_absolute = resolve_path(args.components_overlay) if args.components_overlay else language.components_overlay
        blueprints_absolute = resolve_path(args.blueprints_overlay) if args.blueprints_overlay else language.blueprints_overlay
        user_cfg_absolute = resolve_path(args.user_cfg) if args.user_cfg else language.user_cfg

        for required_path in (modified_absolute, components_absolute, blueprints_absolute):
            if not required_path.exists():
                raise FileNotFoundError(f"Required file missing for {language.code}: {required_path}")
        if (
            translation_absolute is not None
            and not translation_absolute.exists()
            and not language.use_english_source_as_base
        ):
            raise FileNotFoundError(f"Required file missing for {language.code}: {translation_absolute}")
        if user_cfg_absolute is not None and not user_cfg_absolute.exists():
            raise FileNotFoundError(f"Required file missing for {language.code}: {user_cfg_absolute}")

        if translation_absolute is None:
            translation_data = read_global_ini(english_absolute)
            translation_map: dict[str, str] = {}
        elif translation_absolute is not None and translation_absolute.exists() and translation_absolute.stat().st_size == 0 and language.use_english_source_as_base:
            translation_data = read_global_ini(english_absolute)
            translation_map = {}
        elif translation_absolute is not None and not translation_absolute.exists() and language.use_english_source_as_base:
            translation_data = read_global_ini(english_absolute)
            translation_map = {}
        else:
            translation_data = read_global_ini(translation_absolute)
            translation_map = translation_data.mapping

        modified_overlay = read_global_ini(modified_absolute)
        components_overlay = read_global_ini(components_absolute)
        blueprints_overlay = read_global_ini(blueprints_absolute)

        reference_map = english_data.mapping.copy()
        reference_map.update(translation_map)

        resolved_components_overlay_map, missing_component_refs = resolve_reference_map(
            components_overlay.mapping,
            reference_map=reference_map,
        )
        resolved_blueprints_overlay_map, missing_blueprint_refs = resolve_reference_map(
            blueprints_overlay.mapping,
            reference_map=reference_map,
        )

        validation_errors: list[str] = []
        if translation_map:
            validation_errors.extend(
                validate_reference_map(
                    english_map=english_data.mapping,
                    candidate_map=translation_map,
                    label=f"Master memory {language.code}",
                )
            )
        validation_errors.extend(
            validate_reference_map(
                english_map=english_data.mapping,
                candidate_map=modified_overlay.mapping,
                label=f"Overlay modified_global.ini {language.code}",
                validate_tokens=False,
            )
        )
        validation_errors.extend(
            validate_reference_map(
                english_map=english_data.mapping,
                candidate_map=resolved_components_overlay_map,
                label=f"Overlay components.ini {language.code}",
                validate_tokens=False,
            )
        )
        validation_errors.extend(
            validate_reference_map(
                english_map=english_data.mapping,
                candidate_map=resolved_blueprints_overlay_map,
                label=f"Overlay blueprints.ini {language.code}",
                validate_tokens=False,
            )
        )
        if missing_component_refs:
            sample = ", ".join(sorted(missing_component_refs)[:10])
            validation_errors.append(
                f"Overlay components.ini {language.code}: @KEY@ references not resolved ({len(missing_component_refs)}). Examples: {sample}"
            )
        if missing_blueprint_refs:
            sample = ", ".join(sorted(missing_blueprint_refs)[:10])
            validation_errors.append(
                f"Overlay blueprints.ini {language.code}: @KEY@ references not resolved ({len(missing_blueprint_refs)}). Examples: {sample}"
            )

        matched_translation_keys = len(set(translation_map) & set(english_data.mapping))
        if matched_translation_keys == 0 and not language.use_english_source_as_base and not args.allow_empty_translation_memory:
            validation_errors.append(
                f"The master memory for {language.code} does not contain any translated keys that match the current global.ini."
            )

        base_merge = merge_translations(english_data=english_data, translation_map=translation_map)
        base_entries = apply_replacement_overlay(base_entries=base_merge.entries, overlay_map=modified_overlay.mapping)
        components_entries = apply_overlay(base_entries=base_entries, overlay_map=resolved_components_overlay_map)
        blueprints_entries = apply_overlay(base_entries=base_entries, overlay_map=resolved_blueprints_overlay_map)
        combined_entries = apply_overlay(base_entries=components_entries, overlay_map=resolved_blueprints_overlay_map)

        variants = (
            ("base", base_entries),
            ("componentes", components_entries),
            ("blueprints", blueprints_entries),
            ("componentes-blueprints", combined_entries),
        )
        for variant_name, variant_entries in variants:
            validation_errors.extend(
                validate_output_entries(
                    english_entries=english_data.entries,
                    output_entries=variant_entries,
                    label=f"Salida {language.code}/{variant_name}",
                )
            )

        if validation_errors:
            raise ValueError("\n".join(validation_errors))

        language_staging_root = staging_root / language.code
        if language_staging_root.exists():
            shutil.rmtree(language_staging_root)
        language_staging_root.mkdir(parents=True, exist_ok=True)
        write_staged_language_metadata(root=language_staging_root, language=language)

        for variant_name, variant_entries in variants:
            package_root = language_staging_root / variant_name
            package_root.mkdir(parents=True, exist_ok=True)
            zip_path = packages_root / f"star-citizen-{language.code}-{args.version}-{variant_name}.zip"
            create_package(
                package_root=package_root,
                zip_path=zip_path,
                entries=variant_entries,
                game_language=language.game_language,
                user_cfg_source=user_cfg_absolute,
            )

        reported_missing_entries = [] if language.use_english_source_as_base else base_merge.missing
        reported_missing_count = 0 if language.use_english_source_as_base else base_merge.missing_count

        missing_report_path = reports_root / f"missing-keys-{language.code}.ini"
        write_global_ini(entries=reported_missing_entries, path=missing_report_path)
        total_missing += reported_missing_count
        summary_lines.extend(
            (
                "",
                f"# Language: `{language.code}` ({language.label})",
                f"Total of patch keys: {base_merge.total_count}",
                f"Keys present in master memory: {matched_translation_keys}",
                f"Keys with found translation: {base_merge.total_count - reported_missing_count}",
                f"Keys pending translation: {reported_missing_count}",
            )
        )

    summary_lines.append("")

    summary_path = reports_root / "summary.txt"
    with summary_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(summary_lines))

    print(f"Completed build for version {args.version}")
    print(f"Pending translations: {total_missing}")
    print(f"Packages: {packages_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
