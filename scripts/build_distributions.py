from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path

from localization_tools import (
    apply_overlay,
    apply_replacement_overlay,
    merge_translations,
    read_global_ini,
    resolve_path,
    write_global_ini,
)

PLACEHOLDER_RE = re.compile(
    r"(%(?:\d+\$)?[sdif])"
    r"|(\{[^{}\n]+\})"
    r"|(\\n|\\t|\\r|\\\")"
    r"|(\[\[.*?\]\])"
    r"|(<[^>\n]+>)"
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
            f"{label}: contiene {len(unknown_keys)} claves que no existen en el global.ini ingles. "
            f"Ejemplos: {sample}"
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
            errors.append(f"{label}: placeholders o markup alterados en la clave {key}")

    return errors


def validate_output_entries(*, english_entries, output_entries, label: str) -> list[str]:
    errors: list[str] = []
    english_entries = list(english_entries)
    output_entries = list(output_entries)

    if len(english_entries) != len(output_entries):
        errors.append(
            f"{label}: el numero de entradas no coincide con el origen "
            f"({len(output_entries)} vs {len(english_entries)})"
        )
        return errors

    for index, (english_entry, output_entry) in enumerate(zip(english_entries, output_entries), start=1):
        if english_entry.key != output_entry.key:
            errors.append(
                f"{label}: cambio de clave u orden en la linea {index}: "
                f"{english_entry.key} -> {output_entry.key}"
            )
            continue

        english_tokens = extract_tokens(english_entry.value)
        output_tokens = extract_tokens(output_entry.value)
        if not contains_subsequence(output_tokens, english_tokens):
            errors.append(f"{label}: placeholders o markup alterados en la clave {english_entry.key}")

    return errors


def create_package(package_root: Path, zip_path: Path, entries, user_cfg_source: Path) -> None:
    global_ini_path = package_root / "data" / "Localization" / "spanish_(spain)" / "global.ini"
    write_global_ini(entries=entries, path=global_ini_path)
    shutil.copy2(user_cfg_source, package_root / "user.cfg")

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in package_root.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(package_root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera las distribuciones ZIP de localizacion en espanol.")
    parser.add_argument("--english-global-ini", default="input/current/global.ini")
    parser.add_argument("--translation-memory", default="source/translations/base-spanish.ini")
    parser.add_argument("--modified-overlay", default="source/overlays/modified_global.ini")
    parser.add_argument("--components-overlay", default="source/overlays/components.ini")
    parser.add_argument("--blueprints-overlay", default="source/overlays/blueprints.ini")
    parser.add_argument("--user-cfg", default="source/user.cfg")
    parser.add_argument("--version", default="dev")
    parser.add_argument("--output-root", default="dist")
    parser.add_argument(
        "--allow-empty-translation-memory",
        action="store_true",
        help="Permite generar paquetes aunque la memoria maestra no aporte ninguna traduccion base.",
    )
    args = parser.parse_args()

    english_absolute = resolve_path(args.english_global_ini)
    translation_absolute = resolve_path(args.translation_memory)
    modified_absolute = resolve_path(args.modified_overlay)
    components_absolute = resolve_path(args.components_overlay)
    blueprints_absolute = resolve_path(args.blueprints_overlay)
    user_cfg_absolute = resolve_path(args.user_cfg)
    output_absolute = resolve_path(args.output_root)

    for path in (
        english_absolute,
        translation_absolute,
        modified_absolute,
        components_absolute,
        blueprints_absolute,
        user_cfg_absolute,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Falta un archivo requerido: {path}")

    english_data = read_global_ini(english_absolute)
    translation_data = read_global_ini(translation_absolute)
    modified_overlay = read_global_ini(modified_absolute)
    components_overlay = read_global_ini(components_absolute)
    blueprints_overlay = read_global_ini(blueprints_absolute)

    validation_errors: list[str] = []
    validation_errors.extend(
        validate_reference_map(
            english_map=english_data.mapping,
            candidate_map=translation_data.mapping,
            label="Memoria maestra",
        )
    )
    validation_errors.extend(
        validate_reference_map(
            english_map=english_data.mapping,
            candidate_map=modified_overlay.mapping,
            label="Overlay modified_global.ini",
            validate_tokens=False,
        )
    )
    validation_errors.extend(
        validate_reference_map(
            english_map=english_data.mapping,
            candidate_map=components_overlay.mapping,
            label="Overlay components.ini",
            validate_tokens=False,
        )
    )
    validation_errors.extend(
        validate_reference_map(
            english_map=english_data.mapping,
            candidate_map=blueprints_overlay.mapping,
            label="Overlay blueprints.ini",
            validate_tokens=False,
        )
    )

    matched_translation_keys = len(set(translation_data.mapping) & set(english_data.mapping))
    if matched_translation_keys == 0 and not args.allow_empty_translation_memory:
        validation_errors.append(
            "La memoria maestra no contiene ninguna clave traducida que coincida con el global.ini actual. "
            "Rellena source/translations/base-spanish.ini o usa --allow-empty-translation-memory para forzar el build."
        )

    base_merge = merge_translations(english_data=english_data, translation_map=translation_data.mapping)
    base_entries = apply_replacement_overlay(base_entries=base_merge.entries, overlay_map=modified_overlay.mapping)
    components_entries = apply_overlay(base_entries=base_entries, overlay_map=components_overlay.mapping)
    blueprints_entries = apply_overlay(base_entries=base_entries, overlay_map=blueprints_overlay.mapping)
    combined_entries = apply_overlay(base_entries=components_entries, overlay_map=blueprints_overlay.mapping)

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
                label=f"Salida {variant_name}",
            )
        )

    if validation_errors:
        raise ValueError("\n".join(validation_errors))

    version_root = output_absolute / args.version
    packages_root = version_root / "packages"
    staging_root = version_root / "staging"
    reports_root = version_root / "reports"

    for directory in (packages_root, staging_root, reports_root):
        directory.mkdir(parents=True, exist_ok=True)

    for variant_name, variant_entries in variants:
        package_root = staging_root / variant_name
        if package_root.exists():
            shutil.rmtree(package_root)
        package_root.mkdir(parents=True, exist_ok=True)

        zip_path = packages_root / f"star-citizen-es-{args.version}-{variant_name}.zip"
        create_package(
            package_root=package_root,
            zip_path=zip_path,
            entries=variant_entries,
            user_cfg_source=user_cfg_absolute,
        )

    missing_report_path = reports_root / "missing-keys.ini"
    write_global_ini(entries=base_merge.missing, path=missing_report_path)

    summary_path = reports_root / "summary.txt"
    summary_lines = (
        f"Version: {args.version}",
        f"Total de claves del parche: {base_merge.total_count}",
        f"Claves presentes en memoria maestra: {matched_translation_keys}",
        f"Claves con traduccion encontrada: {base_merge.total_count - base_merge.missing_count}",
        f"Claves pendientes de traducir: {base_merge.missing_count}",
        f"Paquetes generados en: {packages_root}",
    )
    with summary_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(summary_lines))

    print(f"Build completado para version {args.version}")
    print(f"Pendientes de traducir: {base_merge.missing_count}")
    print(f"Paquetes: {packages_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
