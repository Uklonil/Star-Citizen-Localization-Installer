from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REVIEW_DIR = Path(__file__).resolve().parent


def run_step(label: str, args: list[str]) -> None:
    print(f"[blueprints-review] {label}")
    completed = subprocess.run(args, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta la suite de revision de blueprints de extremo a extremo."
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--skip-contracts", action="store_true")
    parser.add_argument("--skip-pool-inference", action="store_true")
    args, passthrough = parser.parse_known_args(argv)

    python_exe = str(Path(args.python).expanduser())

    run_step(
        "mission review",
        [
            python_exe,
            str(REVIEW_DIR / "blueprint_mission_review.py"),
            "--mode",
            "both",
            *passthrough,
        ],
    )
    run_step(
        "reward pool review",
        [
            python_exe,
            str(REVIEW_DIR / "blueprint_reward_pool_review.py"),
            "--mode",
            "both",
            *passthrough,
        ],
    )

    if not args.skip_contracts:
        run_step(
            "mission contract links",
            [
                python_exe,
                str(REVIEW_DIR / "extract_mission_contract_links.py"),
                *passthrough,
            ],
        )

    if not args.skip_pool_inference:
        run_step(
            "contract to pool inference",
            [
                python_exe,
                str(REVIEW_DIR / "infer_blueprint_pools_from_contracts.py"),
                *passthrough,
            ],
        )

    print("[blueprints-review] complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
