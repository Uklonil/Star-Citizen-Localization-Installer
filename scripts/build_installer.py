from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER_ROOT = REPO_ROOT / "installer"
BUILD_ROOT = REPO_ROOT / "build" / "installer"
DIST_ROOT = REPO_ROOT / "dist"
ICON_PATH = INSTALLER_ROOT / "assets" / "app-icon.ico"
PYINSTALLER_DATA_PACKAGES = ("flet", "flet_desktop")


def find_version_dir(version: str | None) -> Path:
    if version:
        version_dir = DIST_ROOT / version
        if not version_dir.is_dir():
            raise FileNotFoundError(f"No existe la version indicada en dist: {version_dir}")
        return version_dir

    candidates: list[tuple[float, Path]] = []
    for path in DIST_ROOT.iterdir():
        if (path / "staging").is_dir():
            candidates.append((path.stat().st_mtime, path))

    if not candidates:
        raise FileNotFoundError("No se ha encontrado ninguna salida en dist/*/staging para empaquetar.")

    _, selected = max(candidates, key=lambda item: item[0])
    return selected


def prepare_assets(version_dir: Path) -> Path:
    assets_root = BUILD_ROOT / "installer_assets"
    if assets_root.exists():
        shutil.rmtree(assets_root)

    staging_dir = version_dir / "staging"
    if not staging_dir.is_dir():
        raise FileNotFoundError(f"La version seleccionada no contiene staging: {staging_dir}")

    shutil.copytree(staging_dir, assets_root)
    metadata_dir = assets_root / "_metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    with (metadata_dir / "version.txt").open("w", encoding="utf-8-sig", newline="\n") as file_handle:
        file_handle.write(version_dir.name)
    return assets_root


def run_pyinstaller(*, app_path: Path, assets_root: Path, output_dir: Path, name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ui_texts_root = INSTALLER_ROOT / "ui_texts"
    installer_assets_root = INSTALLER_ROOT / "assets"
    command: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
    ]
    if ICON_PATH.is_file():
        command.extend(
            [
                "--icon",
                str(ICON_PATH),
            ]
        )
    command.extend(
        [
            "--name",
            name,
            "--distpath",
            str(output_dir),
            "--workpath",
            str(BUILD_ROOT / "work"),
            "--specpath",
            str(BUILD_ROOT / "spec"),
            "--add-data",
            f"{assets_root};installer_assets",
            "--add-data",
            f"{ui_texts_root};installer/ui_texts",
            "--add-data",
            f"{installer_assets_root};installer/assets",
            str(app_path),
        ]
    )
    for package_name in PYINSTALLER_DATA_PACKAGES:
        command.extend(
            [
                "--collect-data",
                package_name,
            ]
        )
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el instalador ejecutable de localizacion.")
    parser.add_argument("--version", help="Version concreta bajo dist/<version>. Si se omite, usa la mas reciente.")
    parser.add_argument("--name", default="StarCitizenLocalizationInstaller")
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "dist-installer"))
    args = parser.parse_args()

    version_dir = find_version_dir(args.version)
    assets_root = prepare_assets(version_dir)
    run_pyinstaller(
        app_path=INSTALLER_ROOT / "app.py",
        assets_root=assets_root,
        output_dir=Path(args.output_dir).resolve(),
        name=args.name,
    )

    print(f"Instalador generado con la version {version_dir.name}")
    print(f"Salida: {Path(args.output_dir).resolve() / (args.name + '.exe')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
