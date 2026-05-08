from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_P4K = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k")
DEFAULT_DATA_ROOT = Path("/data/starcitizen")


@dataclass(frozen=True)
class ExtractionPaths:
    game2_root: Path
    raw_root: Path
    export_root: Path
    reports_root: Path
    normalized_game2: Path


def resolve_starbreaker_path(requested_path: str | Path) -> Path:
    candidates = []
    if requested_path:
        candidates.append(Path(requested_path))
    candidates.append(Path("tools/starbreaker/starbreaker.exe"))

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        resolved_candidate = candidate.expanduser()
        if resolved_candidate in seen:
            continue
        seen.add(resolved_candidate)
        unique_candidates.append(resolved_candidate)

    for candidate in unique_candidates:
        if not candidate.exists():
            continue
        if candidate.is_dir():
            nested_exe = candidate / "starbreaker.exe"
            if nested_exe.exists():
                return nested_exe.resolve()
            continue
        return candidate.resolve()

    checked = ", ".join(str(candidate) for candidate in unique_candidates)
    raise FileNotFoundError(f"StarBreaker not found. Checked: {checked}")


def resolve_p4k_path(requested_path: str | Path | None) -> Path:
    if requested_path:
        resolved = Path(requested_path).expanduser()
    else:
        resolved = DEFAULT_P4K
    if not resolved.exists():
        raise FileNotFoundError(f"Data.p4k not found: {resolved}")
    return resolved.resolve()


def build_extraction_paths(data_root: str | Path) -> ExtractionPaths:
    root = Path(data_root).expanduser()
    game2_root = root / "extracts" / "current" / "game2"
    return ExtractionPaths(
        game2_root=game2_root,
        raw_root=game2_root / "raw",
        export_root=game2_root / "exported",
        reports_root=root / "reports" / "blueprints",
        normalized_game2=game2_root / "Game2.dcb",
    )


def ensure_directories(paths: ExtractionPaths) -> None:
    for candidate in (paths.raw_root, paths.export_root, paths.reports_root, REPO_ROOT / "informes"):
        candidate.mkdir(parents=True, exist_ok=True)


def run_command(args: list[str | Path]) -> subprocess.CompletedProcess[str]:
    rendered = [str(arg) for arg in args]
    return subprocess.run(rendered, check=False, text=True)


def extract_game2(*, starbreaker: Path, p4k: Path, raw_root: Path) -> None:
    completed = run_command(
        [
            starbreaker,
            "p4k",
            "extract",
            "--p4k",
            p4k,
            "--filter",
            "**/Game2.dcb",
            "--output",
            raw_root,
        ]
    )
    if completed.returncode != 0:
        raise RuntimeError(f"StarBreaker p4k extraction failed with exit code {completed.returncode}")


def find_extracted_game2(raw_root: Path) -> Path:
    for candidate in raw_root.rglob("Game2.dcb"):
        return candidate
    raise FileNotFoundError("Game2.dcb was not found after extraction")


def export_dcb(*, starbreaker: Path, normalized_game2: Path, export_root: Path) -> int:
    completed = run_command(
        [
            starbreaker,
            "dcb",
            "extract",
            "--dcb",
            normalized_game2,
            "--format",
            "json",
            "--output",
            export_root,
        ]
    )
    return completed.returncode


def run_scan(*, normalized_game2: Path, starbreaker: Path, p4k: Path, reports_root: Path) -> int:
    completed = run_command(
        [
            sys.executable,
            REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "core" / "scan_game2_text.py",
            "--game2",
            normalized_game2,
            "--global-ini",
            REPO_ROOT / "input" / "current" / "global.ini",
            "--template",
            REPO_ROOT / "source" / "blueprints" / "blueprints_template.ini",
            "--pools",
            REPO_ROOT / "source" / "blueprints" / "pools.json",
            "--data-report",
            reports_root / "game2-text-scan.json",
            "--md-report",
            REPO_ROOT / "informes" / "BLUEPRINTS_EXTRACTION_REPORT.md",
            "--starbreaker",
            starbreaker,
            "--p4k",
            p4k,
        ]
    )
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrae Game2.dcb con StarBreaker, exporta DCB opcionalmente y lanza el escaner textual."
    )
    parser.add_argument("--starbreaker", default="tools/starbreaker.exe")
    parser.add_argument("--p4k", default="")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--skip-dcb-export", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    starbreaker = resolve_starbreaker_path(args.starbreaker)
    p4k = resolve_p4k_path(args.p4k or None)
    paths = build_extraction_paths(args.data_root)
    ensure_directories(paths)

    print("== StarBreaker ==")
    print(starbreaker)
    print("== Data.p4k ==")
    print(p4k)
    print("== Extracting Game2.dcb ==")

    extract_game2(starbreaker=starbreaker, p4k=p4k, raw_root=paths.raw_root)
    extracted_game2 = find_extracted_game2(paths.raw_root)
    shutil.copyfile(extracted_game2, paths.normalized_game2)

    print("Normalized Game2.dcb:")
    print(paths.normalized_game2)

    if not args.skip_dcb_export:
        print("== Attempting DCB export ==")
        try:
            export_code = export_dcb(
                starbreaker=starbreaker,
                normalized_game2=paths.normalized_game2,
                export_root=paths.export_root,
            )
            if export_code != 0:
                print(f"WARNING: DCB export failed with exit code {export_code}")
        except Exception as exc:
            print(f"WARNING: DCB export failed: {exc}")

    print("== Scanning Game2.dcb text windows ==")
    scan_code = run_scan(
        normalized_game2=paths.normalized_game2,
        starbreaker=starbreaker,
        p4k=p4k,
        reports_root=paths.reports_root,
    )
    if scan_code != 0:
        return scan_code

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
