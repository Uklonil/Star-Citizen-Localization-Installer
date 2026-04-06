from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceLanguage:
    code: str
    label: str
    game_language: str
    root: Path
    translation_memory: Path | None
    modified_overlay: Path
    components_overlay: Path
    blueprints_overlay: Path
    user_cfg: Path | None
    use_english_source_as_base: bool = False


@dataclass(frozen=True)
class StagedLanguage:
    code: str
    label: str
    game_language: str
    root: Path


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _optional_path(root: Path, relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    return (root / relative_path).resolve()


def discover_source_languages(repo_root: Path) -> list[SourceLanguage]:
    languages_root = repo_root / "source" / "languages"
    discovered: list[SourceLanguage] = []

    if languages_root.is_dir():
        for language_dir in sorted(path for path in languages_root.iterdir() if path.is_dir()):
            metadata_path = language_dir / "language.json"
            if not metadata_path.is_file():
                continue

            metadata = _read_json(metadata_path)
            discovered.append(
                SourceLanguage(
                    code=metadata["code"],
                    label=metadata["label"],
                    game_language=metadata["game_language"],
                    root=language_dir.resolve(),
                    translation_memory=_optional_path(language_dir, metadata.get("translation_memory")),
                    modified_overlay=(language_dir / metadata["modified_overlay"]).resolve(),
                    components_overlay=(language_dir / metadata["components_overlay"]).resolve(),
                    blueprints_overlay=(language_dir / metadata["blueprints_overlay"]).resolve(),
                    user_cfg=_optional_path(language_dir, metadata.get("user_cfg")),
                    use_english_source_as_base=bool(metadata.get("use_english_source_as_base", False)),
                )
            )

    if discovered:
        return discovered

    legacy_root = repo_root / "source"
    return [
        SourceLanguage(
            code="es-es",
            label="Espanol (Espana)",
            game_language="spanish_(spain)",
            root=legacy_root.resolve(),
            translation_memory=(legacy_root / "translations" / "base-spanish.ini").resolve(),
            modified_overlay=(legacy_root / "overlays" / "modified_global.ini").resolve(),
            components_overlay=(legacy_root / "overlays" / "components.ini").resolve(),
            blueprints_overlay=(legacy_root / "overlays" / "blueprints.ini").resolve(),
            user_cfg=(legacy_root / "user.cfg").resolve(),
            use_english_source_as_base=False,
        )
    ]


def find_source_language(repo_root: Path, code: str) -> SourceLanguage:
    for language in discover_source_languages(repo_root):
        if language.code == code:
            return language
    raise KeyError(f"No existe ningun idioma configurado con codigo '{code}'")


def write_staged_language_metadata(*, root: Path, language: SourceLanguage) -> None:
    metadata_dir = root / "_metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = metadata_dir / "language.json"
    payload = {
        "code": language.code,
        "label": language.label,
        "game_language": language.game_language,
    }
    with metadata_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=True, indent=2)
        file_handle.write("\n")


def discover_staged_languages(staging_root: Path) -> list[StagedLanguage]:
    discovered: list[StagedLanguage] = []
    if not staging_root.is_dir():
        return discovered

    for language_dir in sorted(path for path in staging_root.iterdir() if path.is_dir()):
        metadata_path = language_dir / "_metadata" / "language.json"
        if not metadata_path.is_file():
            continue

        metadata = _read_json(metadata_path)
        discovered.append(
            StagedLanguage(
                code=metadata["code"],
                label=metadata["label"],
                game_language=metadata["game_language"],
                root=language_dir.resolve(),
            )
        )

    return discovered
