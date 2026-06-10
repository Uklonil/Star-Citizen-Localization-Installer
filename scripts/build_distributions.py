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
SKILL_BLUEPRINT_SCRIPTS = REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "core"
if str(SKILL_BLUEPRINT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_BLUEPRINT_SCRIPTS))

from scripts.language_support import (
    SourceLanguage,
    discover_source_languages,
    find_source_language,
    write_staged_language_metadata,
)
from blueprint_pool_source import (
    default_contract_metadata_source_path,
    default_blueprint_source_paths,
    generate_reputation_overlay_data,
    generate_blueprints_overlay_data,
    load_contract_metadata_source,
)
from transport_overlay_source import generate_transport_overlay_data
from localization_tools import (
    Entry,
    apply_overlay,
    apply_replacement_overlay,
    append_new_entries,
    merge_overlay_maps,
    merge_translations,
    normalize_global_ini_data,
    read_global_ini,
    resolve_auxiliary_map,
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
KNOWN_EM_TAG_TYPO_RE = re.compile(r"(<EM([1-4])>~mission\([^<\r\n]+\))<EM\2>")


def normalize_known_markup_typos(value: str) -> str:
    return KNOWN_EM_TAG_TYPO_RE.sub(r"\1</EM\2>", value)


def extract_tokens(value: str) -> list[str]:
    normalized_value = normalize_known_markup_typos(value)
    matches = PLACEHOLDER_RE.findall(normalized_value)
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
    allow_unknown_keys: bool = False,
) -> list[str]:
    errors: list[str] = []

    unknown_keys = sorted(set(candidate_map) - set(english_map))
    if unknown_keys and not allow_unknown_keys:
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


def collect_overlay_extra_entries(
    *,
    english_map: dict[str, str],
    overlay_entries: list[Entry],
) -> list[Entry]:
    extras_by_key: dict[str, Entry] = {}
    ordered_keys: list[str] = []

    for entry in overlay_entries:
        if entry.key in english_map:
            continue
        if entry.key not in extras_by_key:
            ordered_keys.append(entry.key)
        extras_by_key[entry.key] = entry

    return [extras_by_key[key] for key in ordered_keys]


def align_overlay_keys_to_english(
    *,
    overlay_map: dict[str, str],
    english_map: dict[str, str],
) -> dict[str, str]:
    normalized_to_english: dict[str, list[str]] = {}
    for english_key in english_map:
        normalized_to_english.setdefault(english_key.split(",", 1)[0], []).append(english_key)

    aligned: dict[str, str] = {}
    for key, value in overlay_map.items():
        if key in english_map:
            aligned[key] = value
            continue

        candidates = normalized_to_english.get(key.split(",", 1)[0], [])
        if len(candidates) == 1:
            aligned[candidates[0]] = value
            continue

        aligned[key] = value

    return aligned


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


def validate_output_entries_with_extras(
    *,
    english_entries,
    output_entries,
    label: str,
    expected_extra_entries: list[Entry],
) -> list[str]:
    english_entries = list(english_entries)
    output_entries = list(output_entries)
    expected_prefix = output_entries[: len(english_entries)]
    errors = validate_output_entries(
        english_entries=english_entries,
        output_entries=expected_prefix,
        label=label,
    )
    if errors:
        return errors

    actual_extras = output_entries[len(english_entries) :]
    if len(actual_extras) != len(expected_extra_entries):
        return [
            f"{label}: the number of appended extra keys does not match the modified_global overlay "
            f"({len(actual_extras)} vs {len(expected_extra_entries)})"
        ]

    for expected_entry, actual_entry in zip(expected_extra_entries, actual_extras):
        if expected_entry.key != actual_entry.key:
            errors.append(
                f"{label}: unexpected extra key order at end of file: "
                f"{actual_entry.key} != {expected_entry.key}"
            )
            continue
        if expected_entry.value != actual_entry.value:
            errors.append(
                f"{label}: appended extra key value mismatch for {actual_entry.key}"
            )

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


def create_archive_from_root(*, archive_root: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in archive_root.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(archive_root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generates ZIP distributions for localization by language.")
    parser.add_argument("--english-global-ini", default="input/current/global.ini")
    parser.add_argument("--language", help="Language code to compile. If omitted, compiles all configured languages.")
    parser.add_argument("--translation-memory")
    parser.add_argument("--modified-overlay")
    parser.add_argument("--components-overlay")
    parser.add_argument("--reputation-overlay")
    parser.add_argument("--blueprints-overlay")
    parser.add_argument("--transport-overlay")
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
    blueprint_template_source, blueprint_pool_source = default_blueprint_source_paths(REPO_ROOT)
    contract_metadata_source = default_contract_metadata_source_path(REPO_ROOT)
    structured_blueprints_available = blueprint_template_source.exists() and blueprint_pool_source.exists()
    structured_reputation_available = contract_metadata_source.exists()
    structured_transport_available = True
    contract_metadata_payload = (
        load_contract_metadata_source(contract_metadata_source)
        if contract_metadata_source.exists()
        else None
    )

    if not english_absolute.exists():
        raise FileNotFoundError(f"Required file missing: {english_absolute}")

    english_data = normalize_global_ini_data(read_global_ini(english_absolute))
    version_root = output_absolute / args.version
    packages_root = version_root / "packages"
    release_packages_root = version_root / "release-packages"
    installer_bundle_root = version_root / "installer-bundle"
    staging_root = version_root / "staging"
    reports_root = version_root / "reports"

    for directory in (packages_root, release_packages_root, installer_bundle_root, staging_root, reports_root):
        directory.mkdir(parents=True, exist_ok=True)

    languages = [find_source_language(resolve_path("."), args.language)] if args.language else discover_source_languages(resolve_path("."))

    summary_lines = [f"Version: {args.version}"]
    if contract_metadata_payload is not None:
        summary_lines.extend(
            (
                f"Contracts metadata source: {contract_metadata_source.relative_to(REPO_ROOT).as_posix()}",
                f"Contracts title metadata: {len(contract_metadata_payload['title_meta'])}",
                f"Contracts description metadata: {len(contract_metadata_payload['description_meta'])}",
            )
        )
    total_missing = 0

    for language in languages:
        translation_absolute = resolve_path(args.translation_memory) if args.translation_memory else language.translation_memory
        modified_absolute = resolve_path(args.modified_overlay) if args.modified_overlay else language.modified_overlay
        components_absolute = resolve_path(args.components_overlay) if args.components_overlay else language.components_overlay
        reputation_absolute = resolve_path(args.reputation_overlay) if args.reputation_overlay else language.reputation_overlay
        blueprints_absolute = resolve_path(args.blueprints_overlay) if args.blueprints_overlay else language.blueprints_overlay
        transport_absolute = resolve_path(args.transport_overlay) if args.transport_overlay else language.transport_overlay
        user_cfg_absolute = resolve_path(args.user_cfg) if args.user_cfg else language.user_cfg

        if args.reputation_overlay:
            reputation_specific_absolute: Path | None = reputation_absolute
            reputation_shared_absolute: Path | None = None
        else:
            reputation_specific_absolute = language.reputation_overlay_specific
            reputation_shared_absolute = language.reputation_overlay_shared

        if args.blueprints_overlay:
            blueprints_specific_absolute: Path | None = blueprints_absolute
            blueprints_shared_absolute: Path | None = None
        else:
            blueprints_specific_absolute = language.blueprints_overlay_specific
            blueprints_shared_absolute = language.blueprints_overlay_shared

        if args.transport_overlay:
            transport_specific_absolute: Path | None = transport_absolute
            transport_shared_absolute: Path | None = None
        else:
            transport_specific_absolute = language.transport_overlay_specific
            transport_shared_absolute = language.transport_overlay_shared

        for required_path in (modified_absolute, components_absolute):
            if not required_path.exists():
                raise FileNotFoundError(f"Required file missing for {language.code}: {required_path}")
        if (
            reputation_specific_absolute is None
            and reputation_shared_absolute is None
            and not structured_reputation_available
        ):
            raise FileNotFoundError(
                f"Required file missing for {language.code}: {reputation_absolute}"
            )
        for reputation_candidate in (reputation_shared_absolute, reputation_specific_absolute):
            if reputation_candidate is not None and not reputation_candidate.exists():
                if not (
                    structured_reputation_available
                    and reputation_shared_absolute is not None
                    and reputation_candidate == reputation_shared_absolute
                ):
                    raise FileNotFoundError(f"Required file missing for {language.code}: {reputation_candidate}")
        if (
            transport_specific_absolute is None
            and transport_shared_absolute is None
            and not structured_transport_available
        ):
            raise FileNotFoundError(
                f"Required file missing for {language.code}: {transport_absolute}"
            )
        for transport_candidate in (transport_shared_absolute, transport_specific_absolute):
            if transport_candidate is not None and not transport_candidate.exists():
                if not (
                    structured_transport_available
                    and transport_shared_absolute is not None
                    and transport_candidate == transport_shared_absolute
                ):
                    raise FileNotFoundError(f"Required file missing for {language.code}: {transport_candidate}")
        if (
            blueprints_specific_absolute is None
            and blueprints_shared_absolute is None
            and not structured_blueprints_available
        ):
            raise FileNotFoundError(
                f"Required file missing for {language.code}: {blueprints_absolute}"
            )
        for blueprints_candidate in (blueprints_shared_absolute, blueprints_specific_absolute):
            if blueprints_candidate is not None and not blueprints_candidate.exists():
                if not (
                    structured_blueprints_available
                    and blueprints_shared_absolute is not None
                    and blueprints_candidate == blueprints_shared_absolute
                ):
                    raise FileNotFoundError(f"Required file missing for {language.code}: {blueprints_candidate}")
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
        generated_shared_reputation_overlay = None
        if structured_reputation_available and not args.reputation_overlay:
            generated_shared_reputation_overlay = generate_reputation_overlay_data(
                contract_metadata_path=contract_metadata_source,
            )
        generated_shared_transport_overlay = None
        if structured_transport_available and not args.transport_overlay:
            generated_shared_transport_overlay = generate_transport_overlay_data(
                english_data=english_data,
            )
        generated_shared_blueprints_overlay = None
        if structured_blueprints_available and not args.blueprints_overlay:
            generated_shared_blueprints_overlay = generate_blueprints_overlay_data(
                template_path=blueprint_template_source,
                pool_source_path=blueprint_pool_source,
            )

        shared_reputation_overlay = (
            generated_shared_reputation_overlay
            if generated_shared_reputation_overlay is not None
            else (read_global_ini(reputation_shared_absolute) if reputation_shared_absolute is not None else None)
        )
        specific_reputation_overlay = (
            read_global_ini(reputation_specific_absolute) if reputation_specific_absolute is not None else None
        )
        reputation_overlay_map = merge_overlay_maps(
            shared_reputation_overlay.mapping if shared_reputation_overlay is not None else {},
            specific_reputation_overlay.mapping if specific_reputation_overlay is not None else {},
        )
        reputation_overlay_map = align_overlay_keys_to_english(
            overlay_map=reputation_overlay_map,
            english_map=english_data.mapping,
        )
        shared_transport_overlay = (
            generated_shared_transport_overlay
            if generated_shared_transport_overlay is not None
            else (read_global_ini(transport_shared_absolute) if transport_shared_absolute is not None else None)
        )
        specific_transport_overlay = (
            read_global_ini(transport_specific_absolute) if transport_specific_absolute is not None else None
        )
        transport_overlay_map = merge_overlay_maps(
            shared_transport_overlay.mapping if shared_transport_overlay is not None else {},
            specific_transport_overlay.mapping if specific_transport_overlay is not None else {},
        )
        transport_overlay_map = align_overlay_keys_to_english(
            overlay_map=transport_overlay_map,
            english_map=english_data.mapping,
        )
        shared_blueprints_overlay = (
            generated_shared_blueprints_overlay
            if generated_shared_blueprints_overlay is not None
            else (read_global_ini(blueprints_shared_absolute) if blueprints_shared_absolute is not None else None)
        )
        specific_blueprints_overlay = (
            read_global_ini(blueprints_specific_absolute) if blueprints_specific_absolute is not None else None
        )
        blueprints_overlay_map = merge_overlay_maps(
            shared_blueprints_overlay.mapping if shared_blueprints_overlay is not None else {},
            specific_blueprints_overlay.mapping if specific_blueprints_overlay is not None else {},
        )
        blueprints_overlay_map = align_overlay_keys_to_english(
            overlay_map=blueprints_overlay_map,
            english_map=english_data.mapping,
        )
        auxiliary_keys_map = (
            read_global_ini(language.auxiliary_keys).mapping if language.auxiliary_keys is not None else {}
        )

        reference_map = english_data.mapping.copy()
        reference_map.update(translation_map)

        resolved_components_overlay_map, missing_component_refs = resolve_reference_map(
            components_overlay.mapping,
            reference_map=reference_map,
        )
        reputation_overlay_with_aux_map, missing_reputation_auxiliary_refs = resolve_auxiliary_map(
            reputation_overlay_map,
            auxiliary_map=auxiliary_keys_map,
        )
        resolved_reputation_overlay_map, missing_reputation_refs = resolve_reference_map(
            reputation_overlay_with_aux_map,
            reference_map=reference_map,
        )
        transport_overlay_with_aux_map, missing_transport_auxiliary_refs = resolve_auxiliary_map(
            transport_overlay_map,
            auxiliary_map=auxiliary_keys_map,
        )
        resolved_transport_overlay_map, missing_transport_refs = resolve_reference_map(
            transport_overlay_with_aux_map,
            reference_map=reference_map,
        )
        blueprints_overlay_with_aux_map, missing_auxiliary_refs = resolve_auxiliary_map(
            blueprints_overlay_map,
            auxiliary_map=auxiliary_keys_map,
        )
        resolved_blueprints_overlay_map, missing_blueprint_refs = resolve_reference_map(
            blueprints_overlay_with_aux_map,
            reference_map=reference_map,
        )

        validation_errors: list[str] = []
        if translation_map:
            validation_errors.extend(
                validate_reference_map(
                    english_map=english_data.mapping,
                    candidate_map=translation_map,
                    label=f"Master memory {language.code}",
                    allow_unknown_keys=True,
                )
            )
        validation_errors.extend(
            validate_reference_map(
                english_map=english_data.mapping,
                candidate_map=modified_overlay.mapping,
                label=f"Overlay modified_global.ini {language.code}",
                validate_tokens=False,
                allow_unknown_keys=True,
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
                candidate_map=reputation_overlay_with_aux_map,
                label=f"Overlay reputation.ini {language.code}",
                validate_tokens=False,
            )
        )
        validation_errors.extend(
            validate_reference_map(
                english_map=english_data.mapping,
                candidate_map=transport_overlay_with_aux_map,
                label=f"Overlay transport.ini {language.code}",
                validate_tokens=False,
            )
        )
        validation_errors.extend(
            validate_reference_map(
                english_map=english_data.mapping,
                candidate_map=blueprints_overlay_with_aux_map,
                label=f"Overlay blueprints.ini {language.code}",
                validate_tokens=False,
            )
        )
        if missing_reputation_auxiliary_refs:
            sample = ", ".join(sorted(missing_reputation_auxiliary_refs)[:10])
            validation_errors.append(
                f"Overlay reputation.ini {language.code}: ##auxiliary## references not resolved ({len(missing_reputation_auxiliary_refs)}). Examples: {sample}"
            )
        if missing_reputation_refs:
            sample = ", ".join(sorted(missing_reputation_refs)[:10])
            validation_errors.append(
                f"Overlay reputation.ini {language.code}: @KEY@ references not resolved ({len(missing_reputation_refs)}). Examples: {sample}"
            )
        if missing_transport_auxiliary_refs:
            sample = ", ".join(sorted(missing_transport_auxiliary_refs)[:10])
            validation_errors.append(
                f"Overlay transport.ini {language.code}: ##auxiliary## references not resolved ({len(missing_transport_auxiliary_refs)}). Examples: {sample}"
            )
        if missing_transport_refs:
            sample = ", ".join(sorted(missing_transport_refs)[:10])
            validation_errors.append(
                f"Overlay transport.ini {language.code}: @KEY@ references not resolved ({len(missing_transport_refs)}). Examples: {sample}"
            )
        if missing_auxiliary_refs:
            sample = ", ".join(sorted(missing_auxiliary_refs)[:10])
            validation_errors.append(
                f"Overlay blueprints.ini {language.code}: ##auxiliary## references not resolved ({len(missing_auxiliary_refs)}). Examples: {sample}"
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

        modified_overlay_extra_entries = collect_overlay_extra_entries(
            english_map=english_data.mapping,
            overlay_entries=modified_overlay.entries,
        )
        base_merge = merge_translations(english_data=english_data, translation_map=translation_map)
        base_entries = apply_replacement_overlay(base_entries=base_merge.entries, overlay_map=modified_overlay.mapping)
        base_entries = append_new_entries(base_entries, extra_entries=modified_overlay_extra_entries)
        components_entries = apply_overlay(base_entries=base_entries, overlay_map=resolved_components_overlay_map)
        reputation_entries = apply_overlay(base_entries=base_entries, overlay_map=resolved_reputation_overlay_map)
        components_reputation_entries = apply_overlay(base_entries=components_entries, overlay_map=resolved_reputation_overlay_map)
        blueprints_entries = apply_overlay(base_entries=reputation_entries, overlay_map=resolved_blueprints_overlay_map)
        combined_entries = apply_overlay(base_entries=components_reputation_entries, overlay_map=resolved_blueprints_overlay_map)
        transport_entries = apply_overlay(base_entries=blueprints_entries, overlay_map=resolved_transport_overlay_map)
        combined_transport_entries = apply_overlay(base_entries=combined_entries, overlay_map=resolved_transport_overlay_map)

        variants = (
            ("base", base_entries),
            ("componentes", components_entries),
            ("blueprints", transport_entries),
            ("componentes-blueprints", combined_transport_entries),
        )
        for variant_name, variant_entries in variants:
            validation_errors.extend(
                validate_output_entries_with_extras(
                    english_entries=english_data.entries,
                    output_entries=variant_entries,
                    label=f"Salida {language.code}/{variant_name}",
                    expected_extra_entries=modified_overlay_extra_entries,
                )
            )

        reported_missing_entries = [] if language.use_english_source_as_base else base_merge.missing
        reported_missing_count = 0 if language.use_english_source_as_base else base_merge.missing_count
        if reported_missing_count > 0 and not args.allow_empty_translation_memory:
            sample = ", ".join(entry.key for entry in reported_missing_entries[:10])
            validation_errors.append(
                f"The master memory for {language.code} is missing {reported_missing_count} keys from the current global.ini. "
                f"Examples: {sample}"
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

        release_zip_path = release_packages_root / f"star-citizen-{language.code}-{args.version}.zip"
        create_package(
            package_root=language_staging_root / "componentes-blueprints",
            zip_path=release_zip_path,
            entries=combined_transport_entries,
            game_language=language.game_language,
            user_cfg_source=user_cfg_absolute,
        )

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
    with summary_path.open("w", encoding="utf-8-sig", newline="\n") as file_handle:
        file_handle.write("\n".join(summary_lines))

    installer_bundle_zip_path = installer_bundle_root / f"star-citizen-installer-assets-{args.version}.zip"
    create_archive_from_root(
        archive_root=staging_root,
        zip_path=installer_bundle_zip_path,
    )

    print(f"Completed build for version {args.version}")
    print(f"Pending translations: {total_missing}")
    print(f"Packages: {packages_root}")
    print(f"Release packages: {release_packages_root}")
    print(f"Installer bundle: {installer_bundle_zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
