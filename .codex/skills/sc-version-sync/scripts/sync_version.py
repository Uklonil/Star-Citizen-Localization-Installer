from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import hashlib
import json
import os
import re


DEFAULT_STATE = Path("/data/starcitizen/state/last_patch.json")
DEFAULT_VERSION = Path("VERSION")
DEFAULT_REPORT = Path("informes/version-sync-report.md")


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def detect_version_from_path(p4k: Path) -> str:
    env_version = os.environ.get("SC_PATCH_VERSION")
    if env_version:
        return env_version

    launcher_version = detect_version_from_launcher_logs(p4k)
    if launcher_version:
        return launcher_version

    manifest_version = detect_version_from_build_manifest(p4k)
    if manifest_version:
        return manifest_version

    return f"unknown-{int(p4k.stat().st_mtime)}"


def detect_version_from_build_manifest(p4k: Path) -> str | None:
    manifest_path = p4k.parent / "build_manifest.id"

    if not manifest_path.exists():
        return None

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    data = payload.get("Data")
    if not isinstance(data, dict):
        return None

    channel = p4k.parent.name.lower()
    if not channel:
        channel = "live"

    requested_change = str(data.get("RequestedP4ChangeNum") or "").strip()
    branch = str(data.get("Branch") or "").strip()
    raw_version = str(data.get("Version") or "").strip()

    base_version = extract_base_version(branch) or extract_base_version(raw_version)
    if not base_version:
        return None

    if requested_change and requested_change.lower() != "none":
        return f"{base_version}-{channel}.{requested_change}"

    return f"{base_version}-{channel}"


def detect_version_from_launcher_logs(p4k: Path) -> str | None:
    metadata = read_launcher_log_metadata(p4k)
    return metadata["version_label"]


def extract_base_version(value: str) -> str | None:
    if not value:
        return None

    match = re.search(r"(\d+\.\d+\.\d+)", value)
    if match:
        return match.group(1)

    return None


def read_launcher_log_metadata(p4k: Path) -> dict[str, str | None]:
    channel = p4k.parent.name.upper()
    requested_change = read_build_manifest_metadata(p4k)["change"]
    log_path = Path(os.environ.get("APPDATA", "")) / "rsilauncher" / "logs" / "log.log"
    metadata = {
        "path": str(log_path),
        "version_label": None,
    }

    if not requested_change or requested_change.lower() == "none":
        return metadata

    if not log_path.exists():
        return metadata

    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return metadata

    pattern = re.compile(
        rf"Star Citizen {re.escape(channel)} "
        rf"(\d+\.\d+\.\d+-{channel.lower()}\.{re.escape(requested_change)})"
    )

    for line in reversed(lines):
        match = pattern.search(line)
        if match:
            metadata["version_label"] = match.group(1)
            return metadata

    return metadata


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temp = path.with_suffix(".tmp")

    temp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    temp.replace(path)


def write_report(path: Path, report: dict) -> None:
    lines = [
        "# Version Sync Report",
        "",
        f"- Timestamp: `{report['timestamp']}`",
        f"- VERSION before: `{report['previous_version']}`",
        f"- VERSION after: `{report['current_version']}`",
        f"- Data.p4k: `{report['p4k_path']}`",
        f"- Data.p4k size: `{report['p4k_size']}`",
        f"- Data.p4k modified: `{report['p4k_mtime']}`",
        f"- Detected channel: `{report['channel']}`",
        f"- Launcher log path: `{report['launcher_log_path']}`",
        f"- Launcher version label: `{report['launcher_version_label']}`",
        f"- Build manifest path: `{report['build_manifest_path']}`",
        f"- Build manifest branch: `{report['build_manifest_branch']}`",
        f"- Build manifest version: `{report['build_manifest_version']}`",
        f"- Build manifest change: `{report['build_manifest_change']}`",
        f"- global.ini hash: `{report['global_ini_hash']}`",
        f"- Game2.dcb hash: `{report['game2_hash']}`",
        "",
        "## Change detection",
        "",
        f"- Patch changed: `{report['patch_changed']}`",
        f"- global.ini changed: `{report['global_ini_changed']}`",
        f"- Game2.dcb changed: `{report['game2_changed']}`",
        "",
        "## Recommended workflow",
        "",
    ]

    for step in report["recommended_workflow"]:
        lines.append(f"- {step}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_build_manifest_metadata(p4k: Path) -> dict[str, str | None]:
    manifest_path = p4k.parent / "build_manifest.id"
    metadata = {
        "path": str(manifest_path),
        "branch": None,
        "version": None,
        "change": None,
    }

    if not manifest_path.exists():
        return metadata

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return metadata

    data = payload.get("Data")
    if not isinstance(data, dict):
        return metadata

    metadata["branch"] = str(data.get("Branch") or "").strip() or None
    metadata["version"] = str(data.get("Version") or "").strip() or None
    metadata["change"] = str(data.get("RequestedP4ChangeNum") or "").strip() or None
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p4k", required=True)
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--version-file", default=str(DEFAULT_VERSION))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))

    args = parser.parse_args()

    p4k = Path(args.p4k)
    state_path = Path(args.state)
    version_file = Path(args.version_file)
    report_path = Path(args.report)

    if not p4k.exists():
        raise SystemExit(f"Data.p4k not found: {p4k}")

    previous_state = load_state(state_path)

    current_version = detect_version_from_path(p4k)
    manifest_metadata = read_build_manifest_metadata(p4k)
    launcher_metadata = read_launcher_log_metadata(p4k)

    global_ini = Path("input/current/global.ini")
    game2 = Path("/data/starcitizen/extracts/current/game2/Game2.dcb")

    current = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "current_version": current_version,
        "p4k_path": str(p4k),
        "p4k_size": p4k.stat().st_size,
        "p4k_mtime": datetime.fromtimestamp(
            p4k.stat().st_mtime
        ).isoformat(timespec="seconds"),
        "channel": p4k.parent.name.lower(),
        "launcher_log_path": launcher_metadata["path"],
        "launcher_version_label": launcher_metadata["version_label"],
        "build_manifest_path": manifest_metadata["path"],
        "build_manifest_branch": manifest_metadata["branch"],
        "build_manifest_version": manifest_metadata["version"],
        "build_manifest_change": manifest_metadata["change"],
        "global_ini_hash": sha256_file(global_ini),
        "game2_hash": sha256_file(game2),
    }

    previous_version = previous_state.get("current_version")

    patch_changed = (
        previous_version != current_version
        or previous_state.get("p4k_size") != current["p4k_size"]
        or previous_state.get("p4k_mtime") != current["p4k_mtime"]
    )

    global_ini_changed = (
        previous_state.get("global_ini_hash") != current["global_ini_hash"]
    )

    game2_changed = (
        previous_state.get("game2_hash") != current["game2_hash"]
    )

    workflow = []

    if patch_changed:
        workflow.extend([
            "run sc-global-ini-sync",
            "run translate-loc if new keys exist",
            "run sc-blueprint-extractor",
            "run build distributions",
        ])
    else:
        workflow.append("skip full extraction workflow")

        if global_ini_changed:
            workflow.append("run localization validation")

        if game2_changed:
            workflow.append("run blueprint extraction only")

    report = {
        **current,
        "previous_version": previous_version,
        "patch_changed": patch_changed,
        "global_ini_changed": global_ini_changed,
        "game2_changed": game2_changed,
        "recommended_workflow": workflow,
    }

    version_file.write_text(current_version + "\n", encoding="utf-8")

    save_json_atomic(state_path, current)

    write_report(report_path, report)

    print("OK")
    print(f"Patch changed: {patch_changed}")
    print(f"global.ini changed: {global_ini_changed}")
    print(f"Game2.dcb changed: {game2_changed}")
    print(f"VERSION updated: {version_file}")
    print(f"State updated: {state_path}")


if __name__ == "__main__":
    main()
