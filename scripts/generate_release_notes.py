from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as file_handle:
        payload = json.load(file_handle)
    if not isinstance(payload, dict):
        raise ValueError(f"El archivo no contiene un objeto JSON valido: {path}")
    return payload


def build_release_notes(*, manifest: dict) -> str:
    version = str(manifest["version"])
    installer = manifest.get("installer")
    languages = manifest.get("languages")
    if not isinstance(languages, dict) or not languages:
        raise ValueError("El manifest no contiene idiomas publicables.")

    lines: list[str] = [
        f"# Star Citizen Localization {version}",
        "",
        "## English",
        "",
        "Choose one of these download paths:",
        "",
        "- Manual install: download the ZIP for your language from this release. These public ZIPs already include all supported overlays.",
        "- Custom install: use the Windows installer if you want to choose overlay combinations such as components or blueprint metadata.",
        "",
    ]

    if isinstance(installer, dict):
        installer_name = installer.get("filename")
        if isinstance(installer_name, str) and installer_name:
            lines.append(f"- Installer: `{installer_name}`")
            lines.append("")

    lines.extend(
        [
            "Available language ZIPs:",
            "",
        ]
    )

    for language_code, payload in languages.items():
        if not isinstance(payload, dict):
            continue
        label = str(payload.get("label", language_code))
        package = payload.get("package")
        if not isinstance(package, dict):
            continue
        filename = str(package.get("filename", ""))
        if not filename:
            continue
        lines.append(f"- `{label}`: `{filename}`")

    lines.extend(
        [
            "",
            "Technical note:",
            "",
            "- `installer-bundle` and `manifest.json` are release assets for the installer update flow. Most users should ignore them.",
            "",
            "## Espanol",
            "",
            "Elige una de estas formas de descarga:",
            "",
            "- Instalacion manual: descarga el ZIP de tu idioma desde esta release. Esos ZIP publicos ya llevan aplicados todos los overlays soportados.",
            "- Instalacion personalizada: usa el instalador de Windows si quieres elegir combinaciones de overlays como componentes o metadatos de blueprints.",
            "",
        ]
    )

    if isinstance(installer, dict):
        installer_name = installer.get("filename")
        if isinstance(installer_name, str) and installer_name:
            lines.append(f"- Instalador: `{installer_name}`")
            lines.append("")

    lines.extend(
        [
            "ZIP disponibles por idioma:",
            "",
        ]
    )

    for language_code, payload in languages.items():
        if not isinstance(payload, dict):
            continue
        label = str(payload.get("label", language_code))
        package = payload.get("package")
        if not isinstance(package, dict):
            continue
        filename = str(package.get("filename", ""))
        if not filename:
            continue
        lines.append(f"- `{label}`: `{filename}`")

    lines.extend(
        [
            "",
            "Nota tecnica:",
            "",
            "- `installer-bundle` y `manifest.json` son assets de soporte para el flujo de actualizacion del instalador. La mayoria de usuarios no necesita descargarlos.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera notas de release legibles para usuarios a partir del manifest.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--output")
    args = parser.parse_args()

    version_root = REPO_ROOT / "dist" / args.version
    manifest_path = Path(args.manifest).resolve() if args.manifest else version_root / "reports" / "manifest.json"
    output_path = Path(args.output).resolve() if args.output else version_root / "reports" / "release-notes.md"

    manifest = read_json(manifest_path)
    notes = build_release_notes(manifest=manifest)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write(notes)
        file_handle.write("\n")

    print(f"Release notes generadas: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
