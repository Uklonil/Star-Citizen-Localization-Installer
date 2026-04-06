from __future__ import annotations

import argparse
from pathlib import Path

from localization_tools import read_global_ini, resolve_path


def choose_key(keys: list[str]) -> str | None:
    if len(keys) == 1:
        return keys[0]

    non_short = [key for key in keys if not key.endswith("_short")]
    if len(non_short) == 1:
        return non_short[0]
    if non_short:
        return sorted(non_short)[0]

    return sorted(keys)[0] if keys else None


def build_value_index(path: Path) -> dict[str, list[str]]:
    data = read_global_ini(path)
    value_to_keys: dict[str, list[str]] = {}

    for entry in data.entries:
        value_to_keys.setdefault(entry.value, []).append(entry.key)

    return value_to_keys


def register_alias(alias_to_keys: dict[str, list[str]], alias: str, keys: list[str]) -> None:
    if alias and alias not in alias_to_keys:
        alias_to_keys[alias] = keys


def build_alias_index(value_to_keys: dict[str, list[str]]) -> dict[str, list[str]]:
    alias_to_keys: dict[str, list[str]] = {}

    for value, keys in value_to_keys.items():
        if value.startswith("Brazo "):
            register_alias(alias_to_keys, f"Brazos {value[6:]}", keys)
        if value.startswith("Pierna "):
            register_alias(alias_to_keys, f"Piernas {value[7:]}", keys)
        if value.startswith("Rifle de francotirador "):
            register_alias(alias_to_keys, value.replace("Rifle de francotirador ", "Fusil de Francotirador ", 1), keys)
        if value.startswith("Rifle francotirador "):
            register_alias(alias_to_keys, value.replace("Rifle francotirador ", "Fusil de Francotirador ", 1), keys)
        if value.startswith("Rifle de Asalto de Energia "):
            register_alias(alias_to_keys, value.replace("de Energia ", "Energetico ", 1), keys)
        if value.startswith("Pistola Laser de Pulsos"):
            register_alias(alias_to_keys, value.replace("de Pulsos", "Pulse"), keys)
        if value.startswith("Subfusil Quartz \""):
            register_alias(alias_to_keys, value.replace("Subfusil Quartz", "Subfusil de Energia Quartz", 1), keys)
        if value == "Pulverizer LMG":
            register_alias(alias_to_keys, "LMG Pulverizer", keys)
        if value == "F55 LMG":
            register_alias(alias_to_keys, "LMG F55", keys)
        if value == "Gallant Rifle":
            register_alias(alias_to_keys, "Fusil Gallant", keys)
        if value == "Rifle Karna":
            register_alias(alias_to_keys, "Fusil Karna", keys)
        if value == "P8-SC SMG":
            register_alias(alias_to_keys, "Subfusil P8-SC", keys)
        if value == "C54 SMG":
            register_alias(alias_to_keys, "Subfusil C54", keys)
        if value == "Bateria de rifle Karna (30 capsulas)":
            register_alias(alias_to_keys, "Bateria de Fusil Karna (35 balas)", keys)
        if value == "Bateria de Pulse Laser Pistol (Cap. 60)":
            register_alias(alias_to_keys, "Bateria de Pistola Laser Pulse (60 balas)", keys)
            register_alias(alias_to_keys, "Bateria de pistola laser Pulse (60 balas)", keys)
        if value == "Bateria Rifle Parallax (80 Cap)":
            register_alias(alias_to_keys, "Bateria de Fusil Parallax (80 balas)", keys)
            register_alias(alias_to_keys, "Bateria de rifle Parallax (80 balas)", keys)
        if value == "Quartz Energy SMG Battery (45 cap)":
            register_alias(alias_to_keys, "Bateria de Subfusil de Energia Quartz (45 balas)", keys)
            register_alias(alias_to_keys, "Bateria de subfusil de energia Quartz (45 balas)", keys)
        if value == "Bateria Fusil Laser Zenith (Cap. 22)":
            register_alias(alias_to_keys, "Bateria de Fusil de Francotirador Laser Zenith (22 balas)", keys)
            register_alias(alias_to_keys, "Bateria de fusil laser Zenith (22 balas)", keys)
        if value == "Bateria de LMG de Energia Fresnel (Cap. 165)":
            register_alias(alias_to_keys, "Bateria de LMG de Energia Fresnel (165 balas)", keys)
        if value == "Gallant Rifle Bateria (45 cap)":
            register_alias(alias_to_keys, "Bateria de Fusil Gallant (45 balas)", keys)
        if value == "Cargador F55 LMG (150 cap)":
            register_alias(alias_to_keys, "Cargador de LMG F55 (150 balas)", keys)
        if value == "Pulverizer LMG Magazine (120 Cap)":
            register_alias(alias_to_keys, "Cargador de LMG Pulverizer (120 balas)", keys)
        if value == "Cargador P8-SC SMG (45 balas)":
            register_alias(alias_to_keys, "Cargador de Subfusil P8-SC (45 balas)", keys)
        if value == " Cargador C54 SMG (40 cap)":
            register_alias(alias_to_keys, "Cargador de Subfusil C54 (50 balas)", keys)
        if value == "Cargador Rifle francotirador A03 (15 cap)":
            register_alias(alias_to_keys, "Cargador de Fusil de Francotirador A03 (15 balas)", keys)
        if value == "Cargador P6-LR (8 balas)":
            register_alias(alias_to_keys, "Cargador de Fusil de Francotirador P6-LR (8 balas)", keys)
        if value == "Rifle de francotirador A03":
            register_alias(alias_to_keys, "Fusil de Francotirador A03", keys)
        if value == "Rifle de francotirador P6-LR":
            register_alias(alias_to_keys, "Fusil de Francotirador P6-LR", keys)
        if value == "Fusil Laser Zenith":
            register_alias(alias_to_keys, "Fusil de Francotirador Laser Zenith", keys)
        if value == "Fusil Laser Zenith \"Darkwave\"":
            register_alias(alias_to_keys, "Fusil Laser Zenith \"Onda Oscura\"", keys)
        if value == "Fusil Laser Zenith \"Landslide\"":
            register_alias(alias_to_keys, "Fusil de Francotirador Laser Zenith \"Landslide\"", keys)
        if value == "Fusil Laser Zenith \"Thunderstrike\"":
            register_alias(alias_to_keys, "Fusil de Francotirador Laser Zenith \"Thunderstrike\"", keys)
        if value == "Karna \"Brimstone":
            register_alias(alias_to_keys, "Fusil Karna \"Brimstone\"", keys)
        if value == "Karna \"Fate\" Rifle":
            register_alias(alias_to_keys, "Fusil Karna \"Fate\"", keys)
        if value == "Rifle Karna \"Rager\"":
            register_alias(alias_to_keys, "Fusil Karna \"Rager\"", keys)
        if value == "Brazos ADP-MK4 Woodland":
            register_alias(alias_to_keys, "Brazos ADP-mk4 Bosque", keys)
        if value == "Torso ADP-MK4 Woodland":
            register_alias(alias_to_keys, "Torso ADP-mk4 Bosque", keys)
        if value == "Piernas ADP-MK4 Woodland":
            register_alias(alias_to_keys, "Piernas ADP-mk4 Bosque", keys)
        if value == "Casco ADP-MK4 Woodland":
            register_alias(alias_to_keys, "Casco ADP-mk4 Bosque", keys)
        if value == "Brazos ADP Bosque":
            register_alias(alias_to_keys, "Brazos ADP Bosque", keys)
        if value == "Piernas ADP Bosque":
            register_alias(alias_to_keys, "Piernas ADP Bosque", keys)
        if value == "ORC-MKX Torso Woodland":
            register_alias(alias_to_keys, "Torso ORC-mkX Bosque", keys)
        if value == "ORC-MKX Brazos Woodland":
            register_alias(alias_to_keys, "Brazos ORC-mkX Bosque", keys)
        if value == "ORC-MKX Piernas Woodland":
            register_alias(alias_to_keys, "Piernas ORC-mkX Bosque", keys)
        if value == "ORC-MKV Bosque":
            register_alias(alias_to_keys, "ORC-mkV Bosque", keys)
        if value == "ORC-MKV Torso Bosque":
            register_alias(alias_to_keys, "Torso ORC-mkV Bosque", keys)
        if value == "Brazos ORC-MKV Bosque":
            register_alias(alias_to_keys, "Brazos ORC-mkV Bosque", keys)
        if value == "Piernas ORC-MKV Bosque":
            register_alias(alias_to_keys, "Piernas ORC-mkV Bosque", keys)
        if value == "Casco G-2 Bosque":
            register_alias(alias_to_keys, "Casco ORC-mkX Bosque", keys)
        if value == "Brazos Corbel Halcyon":
            register_alias(alias_to_keys, "Torso Corbel Halcyon", value_to_keys.get("Pecho Corbel Halcyon", []))
        if value == "Brazos Corbel Mire":
            register_alias(alias_to_keys, "Torso Corbel Mire", value_to_keys.get("Pecho Corbel Mire", []))
        if value == "Brazos Corbel Patina":
            register_alias(alias_to_keys, "Torso Corbel Patina", value_to_keys.get("Pecho Corbel Patina", []))
        if value == "Brazos Corbel Smolder":
            register_alias(alias_to_keys, "Torso Corbel Smolder", value_to_keys.get("Pecho Corbel Smolder", []))
        if value == "Brazo Testudo Velo Nocturno":
            register_alias(alias_to_keys, "Brazos Testudo Nightveil", keys)
        if value == "Torso Testudo Velo Nocturno":
            register_alias(alias_to_keys, "Torso Testudo Nightveil", keys)
        if value == "Casco Testudo Velo Nocturno":
            register_alias(alias_to_keys, "Casco Testudo Nightveil", keys)
        if value == "Piernas Testudo Velo Nocturno":
            register_alias(alias_to_keys, "Piernas Testudo Nightveil", keys)
        if value == "Brazo Testudo Guerra Territorial":
            register_alias(alias_to_keys, "Brazos Testudo Turfwar", keys)
        if value == "Torso Testudo Guerra Territorial":
            register_alias(alias_to_keys, "Torso Testudo Turfwar", keys)
        if value == "Casco Testudo Guerra Territorial":
            register_alias(alias_to_keys, "Casco Testudo Turfwar", keys)
        if value == "Piernas Testudo Guerra Territorial":
            register_alias(alias_to_keys, "Piernas Testudo Turfwar", keys)
        if value == "Brazo Testudo Sacudida Terrestre":
            register_alias(alias_to_keys, "Brazos Testudo Earthshake", keys)
        if value == "Torso Testudo Sacudida Terrestre":
            register_alias(alias_to_keys, "Torso Testudo Earthshake", keys)
        if value == "Casco Testudo Sacudida Terrestre":
            register_alias(alias_to_keys, "Casco Testudo Earthshake", keys)
        if value == "Piernas Testudo Sacudida Terrestre":
            register_alias(alias_to_keys, "Piernas Testudo Earthshake", keys)
        if value == "Chaqueta Carnifex":
            register_alias(alias_to_keys, "Torso Armadura Carnifex", keys)
        if value == "Armadura Carnifex Piernas":
            register_alias(alias_to_keys, "Piernas Armadura Carnifex", keys)
        if value == "Cargador Pistola Tripledown (Cap. 12)":
            register_alias(alias_to_keys, "Cargador de Pistola Tripledown (12 balas)", keys)
        if value == "Brazos Artimex Iman":
            register_alias(alias_to_keys, "Brazos Artimex Lodestone", keys)
        if value == "Piernas de Artimex":
            register_alias(alias_to_keys, "Piernas Artimex", keys)
        if value == "Cargador FS-9 (75 balas)":
            register_alias(alias_to_keys, "Cargador de LMG FS-9 (75 balas)", keys)
        if value == "Cargador de escopeta BR-2 (12 balas)":
            register_alias(alias_to_keys, "Cargador de Escopeta BR-2 (12 balas)", keys)
        if value == "S71 Rifle":
            register_alias(alias_to_keys, "Fusil S71", keys)
        if value == "Cargador de rifle S71 (30 balas)":
            register_alias(alias_to_keys, "Cargador de Fusil S71 (30 balas)", keys)

    return alias_to_keys


def normalize_overlay_lines(
    lines: list[str],
    value_to_keys: dict[str, list[str]],
    alias_to_keys: dict[str, list[str]],
) -> tuple[list[str], int, dict[str, int]]:
    replacements = 0
    unresolved: dict[str, int] = {}
    normalized_lines: list[str] = []

    for raw_line in lines:
        if not raw_line or raw_line.startswith((";", "#")) or "=" not in raw_line:
            normalized_lines.append(raw_line)
            continue

        key, value = raw_line.split("=", 1)
        segments = value.split("\\n- ")
        if len(segments) == 1:
            normalized_lines.append(raw_line)
            continue

        rebuilt_segments = [segments[0]]
        for segment in segments[1:]:
            item, separator, suffix = segment.partition("\\n")
            stripped_item = item.strip()
            if not stripped_item or "@" in stripped_item:
                rebuilt_segments.append(segment)
                continue

            candidate_keys = value_to_keys.get(stripped_item, [])
            if not candidate_keys:
                candidate_keys = alias_to_keys.get(stripped_item, [])
            chosen_key = choose_key(candidate_keys)
            if chosen_key is None:
                unresolved[stripped_item] = unresolved.get(stripped_item, 0) + 1
                rebuilt_segments.append(segment)
                continue

            replaced_item = f"@{chosen_key}@"
            rebuilt_segments.append(f"{replaced_item}{separator}{suffix}")
            replacements += 1

        normalized_value = "\\n- ".join(rebuilt_segments)
        normalized_lines.append(f"{key}={normalized_value}")

    return normalized_lines, replacements, unresolved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reemplaza nombres literales de objetos en blueprints.ini por referencias @KEY@."
    )
    parser.add_argument("--translation-memory", default="source/languages/es-es/translation.ini")
    parser.add_argument("--blueprints-overlay", default="source/languages/es-es/overlays/blueprints.ini")
    parser.add_argument("--report", default="dist/validation/blueprints-reference-normalization.txt")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    translation_path = resolve_path(args.translation_memory)
    overlay_path = resolve_path(args.blueprints_overlay)
    report_path = resolve_path(args.report)

    value_to_keys = build_value_index(translation_path)
    alias_to_keys = build_alias_index(value_to_keys)
    original_lines = overlay_path.read_text(encoding="utf-8-sig").splitlines()
    normalized_lines, replacements, unresolved = normalize_overlay_lines(original_lines, value_to_keys, alias_to_keys)

    if args.write:
        overlay_path.write_text("\n".join(normalized_lines) + "\n", encoding="utf-8")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_lines = [
        f"Overlay: {overlay_path}",
        f"Memoria: {translation_path}",
        f"Reemplazos aplicados: {replacements}",
        f"Nombres sin resolver: {len(unresolved)}",
        "",
        "No resueltos:",
    ]
    for item, count in sorted(unresolved.items(), key=lambda pair: (-pair[1], pair[0])):
        report_lines.append(f"{count}x {item}")
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Reemplazos aplicados: {replacements}")
    print(f"Nombres sin resolver: {len(unresolved)}")
    print(f"Reporte: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
