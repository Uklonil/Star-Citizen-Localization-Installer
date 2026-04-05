from __future__ import annotations

import os
import shutil
import string
import sys
import ctypes
from dataclasses import dataclass
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - solo aplica en Windows
    winreg = None


CHANNELS = ("LIVE", "EPTU", "PTU")
DEFAULT_VARIANT = "base"
VARIANT_LABELS = {
    "base": "Solo traduccion",
    "componentes": "Traduccion + nombres de componentes",
    "blueprints": "Traduccion + marcas [BP]",
    "componentes-blueprints": "Traduccion + componentes + [BP]",
}


@dataclass(frozen=True)
class AssetBundle:
    version: str
    root: Path
    variants: dict[str, Path]


def _installer_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _variant_global_ini_path(variant_dir: Path) -> Path:
    return variant_dir / "data" / "Localization" / "spanish_(spain)" / "global.ini"


def _is_valid_variant_dir(path: Path) -> bool:
    return (path / "user.cfg").is_file() and _variant_global_ini_path(path).is_file()


def discover_asset_bundle() -> AssetBundle:
    bundled_root = _installer_base_dir() / "installer_assets"
    if bundled_root.is_dir():
        variants = discover_variants(bundled_root)
        if variants:
            return AssetBundle(version=read_bundle_version(bundled_root), root=bundled_root, variants=variants)

    dist_root = _installer_base_dir() / "dist"
    candidates: list[tuple[float, Path]] = []
    if dist_root.is_dir():
        for version_dir in dist_root.iterdir():
            staging_dir = version_dir / "staging"
            if staging_dir.is_dir() and discover_variants(staging_dir):
                candidates.append((version_dir.stat().st_mtime, version_dir))

    if not candidates:
        raise FileNotFoundError(
            "No se ha encontrado ningun paquete instalable. Ejecuta antes el build de distribucion."
        )

    _, selected_version_dir = max(candidates, key=lambda item: item[0])
    staging_dir = selected_version_dir / "staging"
    return AssetBundle(
        version=selected_version_dir.name,
        root=staging_dir,
        variants=discover_variants(staging_dir),
    )


def discover_variants(root: Path) -> dict[str, Path]:
    variants: dict[str, Path] = {}
    for variant_name in VARIANT_LABELS:
        variant_dir = root / variant_name
        if _is_valid_variant_dir(variant_dir):
            variants[variant_name] = variant_dir
    return variants


def read_bundle_version(root: Path) -> str:
    version_file = root / "_metadata" / "version.txt"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip() or "desconocida"
    return "desconocida"


def detect_install_paths() -> list[Path]:
    candidates: list[Path] = []

    candidates.extend(_candidate_paths_from_registry())

    env_roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    for env_root in env_roots:
        if env_root:
            root = Path(env_root)
            candidates.extend(_candidate_paths_for_drive(root.drive))

    for drive_letter in string.ascii_uppercase:
        drive = f"{drive_letter}:"
        if Path(f"{drive}\\").exists():
            candidates.extend(_candidate_paths_for_drive(drive))

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        normalized = str(path.resolve()) if path.exists() else str(path)
        if normalized in seen:
            continue
        seen.add(normalized)
        if path.exists():
            unique_candidates.append(path.resolve())

    return unique_candidates


def _candidate_paths_from_registry() -> list[Path]:
    if winreg is None:
        return []

    uninstall_roots = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    )
    hives = (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)

    candidates: list[Path] = []
    for hive in hives:
        for uninstall_root in uninstall_roots:
            try:
                with winreg.OpenKey(hive, uninstall_root) as root_key:
                    for index in range(winreg.QueryInfoKey(root_key)[0]):
                        subkey_name = winreg.EnumKey(root_key, index)
                        with winreg.OpenKey(root_key, subkey_name) as app_key:
                            display_name = _read_registry_value(app_key, "DisplayName")
                            install_location = _read_registry_value(app_key, "InstallLocation")
                            if not display_name or not install_location:
                                continue
                            if "star citizen" not in display_name.lower() and "roberts space industries" not in display_name.lower():
                                continue
                            candidates.append(normalize_install_path(install_location))
            except OSError:
                continue

    return candidates


def _read_registry_value(key, name: str) -> str | None:
    try:
        value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _candidate_paths_for_drive(drive: str) -> list[Path]:
    drive_root = Path(f"{drive}\\")
    base_patterns = (
        drive_root / "Program Files" / "Roberts Space Industries" / "StarCitizen",
        drive_root / "Program Files (x86)" / "Roberts Space Industries" / "StarCitizen",
        drive_root / "Roberts Space Industries" / "StarCitizen",
        drive_root / "RSI" / "StarCitizen",
        drive_root / "Games" / "StarCitizen",
        drive_root / "Games" / "Roberts Space Industries" / "StarCitizen",
    )

    candidates: list[Path] = []
    for base_path in base_patterns:
        for channel in CHANNELS:
            candidates.append(base_path / channel)
    return candidates


def normalize_install_path(raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.name.upper() in CHANNELS:
        return path.resolve()

    existing_channels = [path / channel for channel in CHANNELS if (path / channel).is_dir()]
    if existing_channels:
        return existing_channels[0].resolve()

    return path.resolve()


def is_running_as_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def path_requires_admin(path: str | Path) -> bool:
    resolved = normalize_install_path(path)
    protected_roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ]
    for root in protected_roots:
        if not root:
            continue
        try:
            root_path = Path(root).resolve()
            resolved.relative_to(root_path)
            return True
        except Exception:
            continue
    return False


def install_variant(*, variant_dir: Path, install_root: Path) -> list[Path]:
    if not _is_valid_variant_dir(variant_dir):
        raise FileNotFoundError(f"El paquete seleccionado no es valido: {variant_dir}")

    try:
        install_root.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise PermissionError(
            f"No hay permisos para escribir en {install_root}. Ejecuta el instalador como administrador."
        ) from exc

    copied_files: list[Path] = []
    for source_path in variant_dir.rglob("*"):
        if not source_path.is_file():
            continue

        relative_path = source_path.relative_to(variant_dir)
        destination_path = install_root / relative_path
        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
        except PermissionError as exc:
            raise PermissionError(
                f"No hay permisos para sobrescribir {destination_path}. Ejecuta el instalador como administrador."
            ) from exc
        copied_files.append(relative_path)

    return copied_files
