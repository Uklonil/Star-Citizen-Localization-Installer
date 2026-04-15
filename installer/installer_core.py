from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import string
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from scripts.language_support import discover_staged_languages

try:
    import winreg
except ImportError:  # pragma: no cover - solo aplica en Windows
    winreg = None


CHANNELS = ("LIVE", "EPTU", "PTU")
DEFAULT_VARIANT = "base"
VARIANT_IDS = (
    "base",
    "componentes",
    "blueprints",
    "componentes-blueprints",
)
DEFAULT_RELEASE_REPOSITORY = "Uklonil/Star-Citizen-Localization-Spanish"
RELEASE_API_BASE_URL = f"https://api.github.com/repos/{DEFAULT_RELEASE_REPOSITORY}/releases"
MANIFEST_ASSET_NAME = "manifest.json"
HTTP_TIMEOUT_SECONDS = 20

SEE_MASK_NOCLOSEPROCESS = 0x00000040
INFINITE = 0xFFFFFFFF
ERROR_CANCELLED = 1223


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("fMask", ctypes.c_ulong),
        ("hwnd", ctypes.c_void_p),
        ("lpVerb", ctypes.c_wchar_p),
        ("lpFile", ctypes.c_wchar_p),
        ("lpParameters", ctypes.c_wchar_p),
        ("lpDirectory", ctypes.c_wchar_p),
        ("nShow", ctypes.c_int),
        ("hInstApp", ctypes.c_void_p),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", ctypes.c_wchar_p),
        ("hkeyClass", ctypes.c_void_p),
        ("dwHotKey", ctypes.c_ulong),
        ("hIconOrMonitor", ctypes.c_void_p),
        ("hProcess", ctypes.c_void_p),
    ]


@dataclass(frozen=True)
class VariantBundle:
    name: str
    bundle_version: str
    source_dir: Path | None = None
    package_url: str | None = None
    archive_name: str | None = None
    sha256: str | None = None
    size: int | None = None


@dataclass(frozen=True)
class AssetBundle:
    version: str
    root: Path | None
    languages: dict[str, "LanguageBundle"]
    source: str = "local"
    release_url: str | None = None


@dataclass(frozen=True)
class LanguageBundle:
    code: str
    label: str
    game_language: str
    root: Path | None
    variants: dict[str, VariantBundle]


def _installer_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _variant_global_ini_path(variant_dir: Path, game_language: str) -> Path:
    return variant_dir / "data" / "Localization" / game_language / "global.ini"


def _is_valid_variant_dir(path: Path, game_language: str) -> bool:
    return (path / "user.cfg").is_file() and _variant_global_ini_path(path, game_language).is_file()


def _cache_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "StarCitizenLocalizationInstaller" / "cache"
    return Path.home() / ".star-citizen-localization-installer" / "cache"


def _cache_version_root(version: str) -> Path:
    return _cache_root() / version


def _http_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": "StarCitizenLocalizationInstaller/1.0",
    }


def _http_get_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers=_http_headers())
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return response.read()


def _http_get_json(url: str) -> dict:
    payload = json.loads(_http_get_bytes(url).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"La respuesta remota no es un objeto JSON valido: {url}")
    return payload


def _release_api_url(version: str | None = None) -> str:
    if version:
        return f"{RELEASE_API_BASE_URL}/tags/{version}"
    return f"{RELEASE_API_BASE_URL}/latest"


def _download_to_path(*, url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(destination.suffix + ".tmp")
    if temporary_path.exists():
        temporary_path.unlink()
    request = urllib.request.Request(url, headers=_http_headers())
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response, temporary_path.open("wb") as file_handle:
        shutil.copyfileobj(response, file_handle)
    temporary_path.replace(destination)


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_cached_manifest(path: Path) -> dict | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)
    if not isinstance(payload, dict):
        return None
    return payload


def _write_cached_manifest(*, version: str, manifest: dict) -> None:
    manifest_path = _cache_version_root(version) / MANIFEST_ASSET_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        json.dump(manifest, file_handle, ensure_ascii=True, indent=2)
        file_handle.write("\n")


def _extract_remote_manifest(release_payload: dict) -> tuple[dict, str | None]:
    assets = release_payload.get("assets")
    if not isinstance(assets, list):
        raise ValueError("La release remota no contiene la lista de assets esperada.")

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if asset.get("name") != MANIFEST_ASSET_NAME:
            continue
        download_url = asset.get("browser_download_url")
        if not isinstance(download_url, str) or not download_url:
            raise ValueError("El asset del manifest no incluye browser_download_url.")
        manifest = _http_get_json(download_url)
        return manifest, release_payload.get("html_url")

    raise FileNotFoundError(f"La release remota no contiene el asset requerido '{MANIFEST_ASSET_NAME}'.")


def _variant_from_manifest(*, version: str, variant_name: str, payload: dict) -> VariantBundle:
    url = payload.get("url")
    archive_name = payload.get("filename")
    if not isinstance(url, str) or not url:
        raise ValueError(f"El manifest no contiene una URL valida para la variante '{variant_name}'.")
    if not isinstance(archive_name, str) or not archive_name:
        raise ValueError(f"El manifest no contiene un nombre de archivo valido para la variante '{variant_name}'.")

    sha256 = payload.get("sha256")
    size = payload.get("size")
    return VariantBundle(
        name=variant_name,
        bundle_version=version,
        package_url=url,
        archive_name=archive_name,
        sha256=sha256 if isinstance(sha256, str) and sha256 else None,
        size=int(size) if isinstance(size, int) else None,
    )


def _bundle_from_manifest(*, manifest: dict, release_url: str | None) -> AssetBundle:
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("El manifest remoto no contiene un campo 'version' valido.")

    languages_payload = manifest.get("languages")
    if not isinstance(languages_payload, dict) or not languages_payload:
        raise ValueError("El manifest remoto no contiene idiomas publicables.")

    languages: dict[str, LanguageBundle] = {}
    for language_code, language_payload in languages_payload.items():
        if not isinstance(language_payload, dict):
            continue

        label = language_payload.get("label")
        game_language = language_payload.get("game_language")
        variants_payload = language_payload.get("variants")
        if not isinstance(label, str) or not isinstance(game_language, str) or not isinstance(variants_payload, dict):
            continue

        variants: dict[str, VariantBundle] = {}
        for variant_name in VARIANT_IDS:
            variant_payload = variants_payload.get(variant_name)
            if isinstance(variant_payload, dict):
                variants[variant_name] = _variant_from_manifest(
                    version=version,
                    variant_name=variant_name,
                    payload=variant_payload,
                )

        if not variants:
            continue

        languages[language_code] = LanguageBundle(
            code=language_code,
            label=label,
            game_language=game_language,
            root=None,
            variants=variants,
        )

    if not languages:
        raise ValueError("El manifest remoto no contiene variantes instalables.")

    return AssetBundle(
        version=version,
        root=_cache_version_root(version) / "staging",
        languages=languages,
        source="remote",
        release_url=release_url,
    )


def _fetch_remote_release_payload(version: str | None = None) -> dict:
    return _http_get_json(_release_api_url(version))


def fetch_remote_asset_bundle(version: str | None = None) -> AssetBundle:
    release_payload = _fetch_remote_release_payload(version)
    manifest, release_url = _extract_remote_manifest(release_payload)
    manifest_version = manifest.get("version")
    if isinstance(manifest_version, str) and manifest_version:
        _write_cached_manifest(version=manifest_version, manifest=manifest)
    return _bundle_from_manifest(manifest=manifest, release_url=release_url)


def _local_asset_bundle_candidates() -> list[tuple[float, Path]]:
    candidates: list[tuple[float, Path]] = []
    dist_root = _installer_base_dir() / "dist"
    if not dist_root.is_dir():
        return candidates

    for version_dir in dist_root.iterdir():
        staging_dir = version_dir / "staging"
        if staging_dir.is_dir() and discover_languages(staging_dir, bundle_version=version_dir.name):
            candidates.append((version_dir.stat().st_mtime, version_dir))
    return candidates


def discover_local_asset_bundle(*, version: str | None = None) -> AssetBundle:
    bundled_root = _installer_base_dir() / "installer_assets"
    bundled_version = read_bundle_version(bundled_root)
    bundled_languages = discover_languages(bundled_root, bundle_version=bundled_version)
    if bundled_root.is_dir() and bundled_languages and (version is None or bundled_version == version):
        return AssetBundle(version=bundled_version, root=bundled_root, languages=bundled_languages, source="local")

    candidates = _local_asset_bundle_candidates()
    if version is not None:
        version_dir = _installer_base_dir() / "dist" / version
        staging_dir = version_dir / "staging"
        languages = discover_languages(staging_dir, bundle_version=version) if staging_dir.is_dir() else {}
        if languages:
            return AssetBundle(version=version, root=staging_dir, languages=languages, source="local")
        raise FileNotFoundError(f"No se ha encontrado ningun paquete local para la version {version}.")

    if not candidates:
        raise FileNotFoundError(
            "No se ha encontrado ningun paquete instalable. Ejecuta antes el build de distribucion."
        )

    _, selected_version_dir = max(candidates, key=lambda item: item[0])
    staging_dir = selected_version_dir / "staging"
    return AssetBundle(
        version=selected_version_dir.name,
        root=staging_dir,
        languages=discover_languages(staging_dir, bundle_version=selected_version_dir.name),
        source="local",
    )


def discover_asset_bundle() -> AssetBundle:
    try:
        return discover_local_asset_bundle()
    except FileNotFoundError:
        return fetch_remote_asset_bundle()


def load_asset_bundle(*, source: str | None = None, version: str | None = None) -> AssetBundle:
    if source == "remote":
        cached_manifest = _read_cached_manifest(_cache_version_root(version or "latest") / MANIFEST_ASSET_NAME) if version else None
        if cached_manifest is not None:
            try:
                return _bundle_from_manifest(manifest=cached_manifest, release_url=None)
            except Exception:
                pass
        return fetch_remote_asset_bundle(version)
    if source == "local":
        return discover_local_asset_bundle(version=version)
    return discover_asset_bundle()


def discover_variants(root: Path, *, game_language: str, bundle_version: str) -> dict[str, VariantBundle]:
    variants: dict[str, VariantBundle] = {}
    for variant_name in VARIANT_IDS:
        variant_dir = root / variant_name
        if _is_valid_variant_dir(variant_dir, game_language):
            variants[variant_name] = VariantBundle(
                name=variant_name,
                bundle_version=bundle_version,
                source_dir=variant_dir,
            )
    return variants


def discover_languages(root: Path, *, bundle_version: str) -> dict[str, LanguageBundle]:
    languages: dict[str, LanguageBundle] = {}
    for staged_language in discover_staged_languages(root):
        variants = discover_variants(
            staged_language.root,
            game_language=staged_language.game_language,
            bundle_version=bundle_version,
        )
        if not variants:
            continue
        languages[staged_language.code] = LanguageBundle(
            code=staged_language.code,
            label=staged_language.label,
            game_language=staged_language.game_language,
            root=staged_language.root,
            variants=variants,
        )
    return languages


def read_bundle_version(root: Path) -> str:
    version_file = root / "_metadata" / "version.txt"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip() or "desconocida"
    return "desconocida"


def _cached_variant_root(*, version: str, language_code: str, variant_name: str) -> Path:
    return _cache_version_root(version) / "staging" / language_code / variant_name


def _cached_archive_path(*, version: str, archive_name: str) -> Path:
    return _cache_version_root(version) / "downloads" / archive_name


def ensure_variant_source_dir(*, variant: VariantBundle, language_code: str, game_language: str) -> Path:
    if variant.source_dir is not None:
        if not _is_valid_variant_dir(variant.source_dir, game_language):
            raise FileNotFoundError(f"El paquete local seleccionado no es valido: {variant.source_dir}")
        return variant.source_dir

    if not variant.package_url or not variant.archive_name:
        raise FileNotFoundError(f"La variante '{variant.name}' no contiene origen local ni remoto.")

    extract_root = _cached_variant_root(
        version=variant.bundle_version,
        language_code=language_code,
        variant_name=variant.name,
    )
    if _is_valid_variant_dir(extract_root, game_language):
        return extract_root

    archive_path = _cached_archive_path(version=variant.bundle_version, archive_name=variant.archive_name)
    needs_download = not archive_path.is_file()
    if not needs_download and variant.sha256:
        needs_download = _compute_sha256(archive_path).lower() != variant.sha256.lower()

    if needs_download:
        _download_to_path(url=variant.package_url, destination=archive_path)
        if variant.sha256:
            downloaded_hash = _compute_sha256(archive_path)
            if downloaded_hash.lower() != variant.sha256.lower():
                archive_path.unlink(missing_ok=True)
                raise ValueError(
                    f"El archivo descargado para la variante '{variant.name}' no coincide con el hash esperado."
                )

    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "r") as archive:
        archive.extractall(extract_root)

    if not _is_valid_variant_dir(extract_root, game_language):
        shutil.rmtree(extract_root, ignore_errors=True)
        raise FileNotFoundError(
            f"La variante remota '{variant.name}' no contiene la estructura esperada tras la extraccion."
        )

    return extract_root


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


def run_elevated_process(*, executable_path: Path, arguments: list[str], working_directory: Path | None = None) -> int:
    execute_info = SHELLEXECUTEINFOW()
    execute_info.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
    execute_info.fMask = SEE_MASK_NOCLOSEPROCESS
    execute_info.hwnd = None
    execute_info.lpVerb = "runas"
    execute_info.lpFile = str(executable_path)
    execute_info.lpParameters = subprocess.list2cmdline(arguments)
    execute_info.lpDirectory = str(working_directory) if working_directory is not None else None
    execute_info.nShow = 1

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(execute_info)):
        error_code = ctypes.GetLastError()
        if error_code == ERROR_CANCELLED:
            raise PermissionError("La elevacion fue cancelada por el usuario.")
        raise OSError(f"No se pudo iniciar el proceso elevado. Codigo Win32: {error_code}")

    process_handle = execute_info.hProcess
    if not process_handle:
        raise OSError("No se pudo obtener el handle del proceso elevado.")

    try:
        ctypes.windll.kernel32.WaitForSingleObject(process_handle, INFINITE)
        exit_code = ctypes.c_ulong()
        if not ctypes.windll.kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
            error_code = ctypes.GetLastError()
            raise OSError(f"No se pudo leer el codigo de salida del proceso elevado. Codigo Win32: {error_code}")
        return int(exit_code.value)
    finally:
        ctypes.windll.kernel32.CloseHandle(process_handle)


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


def install_variant(*, variant: VariantBundle, install_root: Path, game_language: str, language_code: str) -> list[Path]:
    variant_dir = ensure_variant_source_dir(
        variant=variant,
        language_code=language_code,
        game_language=game_language,
    )

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
