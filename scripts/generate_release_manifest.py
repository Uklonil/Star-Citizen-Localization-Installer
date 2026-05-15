from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VARIANT_IDS = (
    "base",
    "componentes",
    "blueprints",
    "componentes-blueprints",
)
DEFAULT_REPOSITORY = "Uklonil/Star-Citizen-Localization-Spanish"


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)
    if not isinstance(payload, dict):
        raise ValueError(f"El archivo no contiene un objeto JSON valido: {path}")
    return payload


def source_languages_root() -> Path:
    return REPO_ROOT / "source" / "languages"


def discover_language_metadata() -> dict[str, dict[str, str]]:
    languages: dict[str, dict[str, str]] = {}
    root = source_languages_root()
    for language_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        metadata_path = language_dir / "language.json"
        if not metadata_path.is_file():
            continue
        metadata = read_json(metadata_path)
        code = metadata.get("code")
        label = metadata.get("label")
        game_language = metadata.get("game_language")
        if isinstance(code, str) and isinstance(label, str) and isinstance(game_language, str):
            languages[code] = {
                "label": label,
                "game_language": game_language,
            }
    return languages


def build_variant_payload(*, repository: str, version: str, path: Path) -> dict[str, object]:
    filename = path.name
    return {
        "filename": filename,
        "url": f"https://github.com/{repository}/releases/download/{version}/{filename}",
        "size": path.stat().st_size,
        "sha256": compute_sha256(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera manifest.json para una release publicada en GitHub.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--packages-root")
    parser.add_argument("--installer-path", default="dist-installer/StarCitizenLocalizationInstaller.exe")
    parser.add_argument("--summary-path")
    parser.add_argument("--output")
    args = parser.parse_args()

    version_root = REPO_ROOT / "dist" / args.version
    packages_root = Path(args.packages_root).resolve() if args.packages_root else version_root / "packages"
    summary_path = Path(args.summary_path).resolve() if args.summary_path else version_root / "reports" / "summary.txt"
    output_path = Path(args.output).resolve() if args.output else version_root / "reports" / "manifest.json"
    installer_path = Path(args.installer_path).resolve()

    if not packages_root.is_dir():
        raise FileNotFoundError(f"No existe el directorio de paquetes: {packages_root}")

    language_metadata = discover_language_metadata()
    manifest_languages: dict[str, dict[str, object]] = {}

    for language_code, metadata in language_metadata.items():
        variants: dict[str, dict[str, object]] = {}
        for variant_name in VARIANT_IDS:
            package_name = f"star-citizen-{language_code}-{args.version}-{variant_name}.zip"
            package_path = packages_root / package_name
            if package_path.is_file():
                variants[variant_name] = build_variant_payload(
                    repository=args.repository,
                    version=args.version,
                    path=package_path,
                )

        if variants:
            manifest_languages[language_code] = {
                "label": metadata["label"],
                "game_language": metadata["game_language"],
                "variants": variants,
            }

    if not manifest_languages:
        raise FileNotFoundError("No se ha encontrado ningun paquete ZIP para construir el manifest.")

    payload: dict[str, object] = {
        "schema_version": 1,
        "repository": args.repository,
        "version": args.version,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "languages": manifest_languages,
    }

    if summary_path.is_file():
        payload["summary"] = {
            "filename": summary_path.name,
            "url": f"https://github.com/{args.repository}/releases/download/{args.version}/{summary_path.name}",
            "size": summary_path.stat().st_size,
            "sha256": compute_sha256(summary_path),
        }

    if installer_path.is_file():
        payload["installer"] = {
            "filename": installer_path.name,
            "url": f"https://github.com/{args.repository}/releases/download/{args.version}/{installer_path.name}",
            "size": installer_path.stat().st_size,
            "sha256": compute_sha256(installer_path),
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=True, indent=2)
        file_handle.write("\n")

    print(f"Manifest generado: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
